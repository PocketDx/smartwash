from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import OperationalError
from django.utils import timezone
from rest_framework.test import APITestCase

from ordenes.models import HistorialOrden, Orden, sumar_dias_habiles
from ordenes.tests import CatalogoDePruebaMixin

from .models import Pago

User = get_user_model()
Evento = HistorialOrden.TipoEvento


class PagoApiTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        # 4000 x 2,5 kg + 2000 x 3 prendas = 16000; abono minimo 4800.
        self.registrar(self.prenda(self.lavado, self.planchado))
        self.orden = Orden.objects.get()
        self.url = f"/api/ordenes/{self.orden.pk}/pagos"

    def pagar(self, monto, metodo="efectivo"):
        return self.client.post(self.url, {"monto": monto, "metodo": metodo}, format="json")

    def test_registra_el_pago_y_recalcula_el_estado_de_pago(self):
        response = self.pagar("1000", "transferencia")

        self.assertEqual(response.status_code, 201, response.json())
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.total_pagado(), Decimal("1000"))
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PARCIAL)
        evento = self.orden.historial.last()
        self.assertEqual(evento.tipo_evento, Evento.PAGO)
        self.assertEqual(evento.usuario, self.recepcionista)

    def test_el_pago_total_deja_la_orden_pagada(self):
        self.pagar("16000")

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PAGADA)
        self.assertTrue(self.orden.pago_completo())

    def test_rechaza_montos_no_positivos_o_mayores_al_saldo(self):
        for monto in ("0", "-500", "16000.01"):
            self.assertEqual(self.pagar(monto).status_code, 400, monto)
        self.pagar("10000")
        response = self.pagar("6001")

        self.assertEqual(response.status_code, 400)
        self.assertIn("6000", str(response.json()))
        self.assertEqual(Pago.objects.count(), 1)

    def test_rechaza_un_metodo_de_pago_desconocido(self):
        response = self.pagar("1000", "cheque")

        self.assertEqual(response.status_code, 400)
        self.assertIn("efectivo, transferencia o tarjeta", str(response.json()))

    def test_si_sube_el_total_una_orden_pagada_vuelve_a_parcial(self):
        self.pagar("16000")

        self.client.post(
            f"/api/ordenes/{self.orden.pk}/prendas", self.prenda(self.planchado), format="json"
        )

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PARCIAL)
        self.assertEqual(self.orden.saldo_pendiente(), Decimal("6000"))

    def test_al_alcanzar_el_abono_minimo_la_orden_pasa_a_recibida_con_fecha_estimada(self):
        self.pagar("4800")

        self.orden.refresh_from_db()
        hoy = timezone.localdate()
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.assertEqual(self.orden.abono_alcanzado_en, hoy)
        self.assertEqual(self.orden.fecha_estimada_entrega, sumar_dias_habiles(hoy, 2))
        self.assertEqual(
            list(self.orden.historial.values_list("tipo_evento", flat=True)),
            [Evento.CREACION, Evento.PAGO, Evento.CAMBIO_ESTADO],
        )

    def test_un_pago_menor_al_abono_minimo_deja_la_orden_en_espera(self):
        self.pagar("4799")

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.EN_ESPERA)
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PARCIAL)
        self.assertFalse(self.orden.tiene_abono())
        self.assertIsNone(self.orden.fecha_estimada_entrega)

    def test_varios_pagos_suman_para_el_abono_minimo(self):
        self.pagar("2000")
        self.pagar("2800", "tarjeta")

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)

    def test_la_orden_responde_cuanto_se_ha_pagado_y_conserva_el_abono_si_sube_el_total(self):
        self.pagar("4800")
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/prendas", self.prenda(self.lavado), format="json"
        )

        datos = self.client.get(f"/api/ordenes/{self.orden.pk}").json()

        self.assertEqual(Decimal(datos["total_pagado"]), Decimal("4800"))
        self.assertEqual(Decimal(datos["valor_total"]), Decimal("26000"))
        self.assertEqual(Decimal(datos["saldo_pendiente"]), Decimal("21200"))
        self.assertTrue(datos["tiene_abono"])
        self.assertFalse(datos["pago_completo"])
        self.assertEqual(Decimal(datos["abono_requerido"]), Decimal("4800"))
        self.assertEqual(datos["estado"], Orden.Estado.RECIBIDA)

    def test_el_operario_no_registra_pagos(self):
        operario = User.objects.create_user(username="op", password="x", rol=User.Rol.OPERARIO)
        self.client.force_authenticate(operario)

        self.assertEqual(self.pagar("1000").status_code, 403)
        self.assertFalse(Pago.objects.exists())

    def test_el_estado_de_pago_no_se_fija_a_mano(self):
        self.orden.estado_pago = Orden.EstadoPago.PAGADA
        self.orden.save()

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PENDIENTE)

    def test_los_pagos_no_se_editan_ni_se_eliminan(self):
        self.pagar("1000")
        pago = Pago.objects.get()

        self.assertEqual(self.client.put(f"{self.url}/{pago.pk}", {}).status_code, 404)
        self.assertEqual(self.client.delete(self.url).status_code, 405)
        pago.monto = Decimal("1")
        with self.assertRaises(PermissionDenied):
            pago.save()
        with self.assertRaises(PermissionDenied):
            Pago.objects.all().delete()

    def test_si_falla_la_base_no_queda_el_pago_ni_el_cambio_de_estado(self):
        with (
            mock.patch.object(
                HistorialOrden.objects, "create", side_effect=OperationalError("sin conexion")
            ),
            self.assertLogs("ordenes.historial", level="ERROR"),
        ):
            response = self.pagar("4800")

        self.assertEqual(response.status_code, 503)
        self.orden.refresh_from_db()
        self.assertFalse(Pago.objects.exists())
        self.assertEqual(self.orden.estado, Orden.Estado.EN_ESPERA)
