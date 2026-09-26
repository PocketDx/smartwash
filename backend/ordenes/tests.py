from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from catalogo.models import Servicio, TipoPrenda, Tarifa
from clientes.models import Cliente

from .models import Orden, OrdenServicio, Prenda

User = get_user_model()


class OrdenTests(TestCase):
    def setUp(self):
        self.recepcionista = User.objects.create_user(
            username="recepcion", password="x", rol=User.Rol.RECEPCIONISTA
        )
        self.cliente = Cliente.objects.create(
            documento="1090123456", nombre_completo="Ana Gomez", telefono="3001112233"
        )
        self.camisa = TipoPrenda.objects.create(nombre="Camisa")
        self.lavado = Servicio.objects.create(nombre="Lavado")
        self.planchado = Servicio.objects.create(nombre="Planchado")
        self.tarifa_lavado = self.crear_tarifa(self.lavado, "8000")
        self.tarifa_planchado = self.crear_tarifa(self.planchado, "4000")
        self.orden = Orden.objects.create(
            codigo="ORD-0001",
            cliente=self.cliente,
            recepcionista=self.recepcionista,
        )

    def crear_tarifa(self, servicio, valor):
        return Tarifa.objects.create(
            tipo_prenda=self.camisa,
            servicio=servicio,
            valor=Decimal(valor),
            plazo_entrega_dias=2,
            vigente_desde=date(2026, 1, 1),
        )

    def crear_prenda(self):
        return Prenda.objects.create(orden=self.orden, tipo_prenda=self.camisa)

    def test_el_codigo_de_la_orden_es_unico(self):
        with self.assertRaises(IntegrityError):
            Orden.objects.create(
                codigo="ORD-0001",
                cliente=self.cliente,
                recepcionista=self.recepcionista,
            )

    def test_la_orden_nace_recibida_sin_operario_y_sin_pagar(self):
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PENDIENTE)
        self.assertIsNone(self.orden.operario)

    def test_una_prenda_admite_varios_servicios(self):
        prenda = self.crear_prenda()
        OrdenServicio.objects.create(
            prenda=prenda, tarifa=self.tarifa_lavado, valor_aplicado=Decimal("8000")
        )
        OrdenServicio.objects.create(
            prenda=prenda, tarifa=self.tarifa_planchado, valor_aplicado=Decimal("4000")
        )

        self.assertEqual(prenda.servicios.count(), 2)

    def test_no_repite_el_mismo_servicio_en_una_prenda(self):
        prenda = self.crear_prenda()
        OrdenServicio.objects.create(
            prenda=prenda, tarifa=self.tarifa_lavado, valor_aplicado=Decimal("8000")
        )
        with self.assertRaises(IntegrityError):
            OrdenServicio.objects.create(
                prenda=prenda, tarifa=self.tarifa_lavado, valor_aplicado=Decimal("8000")
            )

    def test_cambiar_la_tarifa_no_altera_lo_ya_cobrado(self):
        prenda = self.crear_prenda()
        servicio = OrdenServicio.objects.create(
            prenda=prenda, tarifa=self.tarifa_lavado, valor_aplicado=Decimal("8000")
        )

        self.tarifa_lavado.valor = Decimal("12000")
        self.tarifa_lavado.save()
        servicio.refresh_from_db()

        self.assertEqual(servicio.valor_aplicado, Decimal("8000"))

    def test_no_se_puede_borrar_un_cliente_con_ordenes(self):
        with self.assertRaises(ProtectedError):
            self.cliente.delete()

    def test_no_se_puede_borrar_una_tarifa_ya_cobrada(self):
        OrdenServicio.objects.create(
            prenda=self.crear_prenda(),
            tarifa=self.tarifa_lavado,
            valor_aplicado=Decimal("8000"),
        )
        with self.assertRaises(ProtectedError):
            self.tarifa_lavado.delete()

    def test_borrar_la_orden_borra_sus_prendas_y_sus_servicios(self):
        prenda = self.crear_prenda()
        OrdenServicio.objects.create(
            prenda=prenda, tarifa=self.tarifa_lavado, valor_aplicado=Decimal("8000")
        )

        self.orden.delete()

        self.assertEqual(Prenda.objects.count(), 0)
        self.assertEqual(OrdenServicio.objects.count(), 0)

    def test_rechaza_una_prenda_con_cantidad_cero(self):
        with self.assertRaises(IntegrityError):
            Prenda.objects.create(
                orden=self.orden, tipo_prenda=self.camisa, cantidad=0
            )

    def test_desactivar_al_operario_no_borra_la_orden(self):
        operario = User.objects.create_user(
            username="op", password="x", rol=User.Rol.OPERARIO
        )
        self.orden.operario = operario
        self.orden.save()

        operario.delete()
        self.orden.refresh_from_db()

        self.assertIsNone(self.orden.operario)
        self.assertEqual(Orden.objects.count(), 1)
