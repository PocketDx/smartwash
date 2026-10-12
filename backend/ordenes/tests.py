from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APITestCase

from catalogo.models import Servicio, TipoPrenda, Tarifa
from clientes.models import Cliente

from .historial import OperacionNoCompletada, operacion_sobre_orden, registrar_evento
from fidelizacion.models import ReglaDescuento

from .models import (
    HistorialOrden,
    Orden,
    OrdenServicio,
    Prenda,
    duracion_estimada_dias,
    sumar_dias_habiles,
)

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

    def test_la_orden_nace_en_espera_sin_operario_y_sin_pagar(self):
        self.assertEqual(self.orden.estado, Orden.Estado.EN_ESPERA)
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


Evento = HistorialOrden.TipoEvento


def crear_orden(codigo="ORD-0100"):
    recepcionista, _ = User.objects.get_or_create(
        username="recepcion", defaults={"rol": User.Rol.RECEPCIONISTA}
    )
    cliente, _ = Cliente.objects.get_or_create(
        documento="1090123456",
        defaults={"nombre_completo": "Ana Gomez", "telefono": "3001112233"},
    )
    return Orden.objects.create(codigo=codigo, cliente=cliente, recepcionista=recepcionista)


class RegistrarEventoTests(TestCase):
    def test_rechaza_un_tipo_de_evento_desconocido(self):
        orden = crear_orden()
        with self.assertRaises(ValueError):
            registrar_evento(orden, "borrado", orden.recepcionista)

    def test_si_falla_el_registro_no_se_aplica_el_cambio_ni_el_historial(self):
        orden = crear_orden()
        with (
            mock.patch.object(
                HistorialOrden.objects, "create", side_effect=OperationalError("sin conexion")
            ),
            self.assertLogs("ordenes.historial", level="ERROR") as logs,
            self.assertRaises(OperacionNoCompletada) as error,
        ):
            with operacion_sobre_orden():
                orden.estado = Orden.Estado.CLASIFICADA
                orden.save()
                registrar_evento(orden, Evento.CAMBIO_ESTADO, orden.recepcionista)

        orden.refresh_from_db()
        self.assertEqual(orden.estado, Orden.Estado.EN_ESPERA)
        self.assertFalse(HistorialOrden.objects.exists())
        self.assertIn("sin conexion", "\n".join(logs.output))
        self.assertNotIn("sin conexion", str(error.exception.detail))


class RegistrarEventoFueraDeTransaccionTests(TransactionTestCase):
    def test_exige_estar_dentro_de_la_transaccion_del_cambio(self):
        orden = crear_orden()
        with self.assertRaises(RuntimeError):
            registrar_evento(orden, Evento.CREACION, orden.recepcionista)


class InmutabilidadHistorialTests(TestCase):
    def setUp(self):
        self.orden = crear_orden()
        self.evento = registrar_evento(
            self.orden, Evento.CREACION, self.orden.recepcionista, "original"
        )

    def test_no_se_puede_editar_un_registro(self):
        self.evento.detalle = "alterado"
        with self.assertRaises(PermissionDenied):
            self.evento.save()
        with self.assertRaises(PermissionDenied):
            HistorialOrden.objects.update(detalle="alterado")
        copia = HistorialOrden(pk=self.evento.pk, orden=self.orden, tipo_evento=Evento.PAGO)
        with self.assertRaises(IntegrityError), transaction.atomic():
            copia.save()

        self.assertEqual(HistorialOrden.objects.get().detalle, "original")

    def test_no_se_puede_borrar_un_registro(self):
        with self.assertRaises(PermissionDenied):
            self.evento.delete()
        with self.assertRaises(PermissionDenied):
            self.orden.historial.all().delete()

        self.assertTrue(HistorialOrden.objects.exists())


class HistorialOrdenApiTests(APITestCase):
    def setUp(self):
        self.orden = crear_orden()
        self.recepcionista = self.orden.recepcionista
        self.admin = User.objects.create_user(
            username="admin", password="x", rol=User.Rol.ADMINISTRADOR
        )
        registrar_evento(self.orden, Evento.CREACION, self.recepcionista, "creada")
        registrar_evento(self.orden, Evento.ASIGNACION, self.admin, "operario1")
        registrar_evento(crear_orden(codigo="ORD-0200"), Evento.CREACION, self.recepcionista)
        self.url = f"/api/ordenes/{self.orden.pk}/historial"

    def test_el_administrador_ve_el_historial_de_la_orden_en_orden_cronologico(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(e["tipo_evento"], e["usuario_nombre"], e["detalle"]) for e in response.json()],
            [(Evento.CREACION, "recepcion", "creada"), (Evento.ASIGNACION, "admin", "operario1")],
        )
        self.assertTrue(all(e["fecha"] for e in response.json()))

    def test_la_recepcionista_consulta_y_el_operario_no(self):
        self.client.force_login(self.recepcionista)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        operario = User.objects.create_user(username="op", password="x", rol=User.Rol.OPERARIO)
        self.client.force_login(operario)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_una_orden_inexistente_responde_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/api/ordenes/9999/historial").status_code, 404)

    def test_la_api_no_permite_escribir_el_historial(self):
        self.client.force_login(self.admin)
        for metodo in ("post", "put", "patch", "delete"):
            response = getattr(self.client, metodo)(self.url, {"detalle": "x"}, format="json")
            self.assertEqual(response.status_code, 405, metodo)

        self.assertEqual(self.orden.historial.count(), 2)


# El manifiesto de WhiteNoise solo existe tras collectstatic; el admin lo necesita para renderizar.
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class HistorialDesdeAdminTests(TestCase):
    def setUp(self):
        self.superusuario = User.objects.create_superuser(
            username="root", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.superusuario)
        self.orden = crear_orden()

    def guardar(self, url, **cambios):
        response = self.client.get(url)
        formularios = [response.context["adminform"].form]
        for inline in response.context["inline_admin_formsets"]:
            formularios.append(inline.formset.management_form)
            formularios.extend(inline.formset.forms)
        datos = {
            campo.html_name: campo.value()
            for formulario in formularios
            for campo in formulario
            if campo.value() is not None
        }
        datos.update(cambios)
        self.assertEqual(self.client.post(url, datos).status_code, 302)

    def editar_orden(self, **cambios):
        self.guardar(f"/admin/ordenes/orden/{self.orden.pk}/change/", **cambios)

    def test_los_cambios_de_la_orden_quedan_en_el_historial(self):
        operario1 = User.objects.create_user(username="operario1", rol=User.Rol.OPERARIO)
        operario2 = User.objects.create_user(username="operario2", rol=User.Rol.OPERARIO)

        self.editar_orden(operario=operario1.pk)
        self.editar_orden(operario=operario2.pk)
        self.editar_orden(estado_pago=Orden.EstadoPago.PAGADA)
        self.editar_orden(estado=Orden.Estado.ENTREGADA)

        self.assertEqual(
            list(self.orden.historial.values_list("tipo_evento", "detalle")),
            [
                (Evento.ASIGNACION, "sin operario → operario1"),
                (Evento.REASIGNACION, "operario1 → operario2"),
                (Evento.PAGO, "Pendiente → Pagada"),
                (Evento.ENTREGA, "En espera → Entregada"),
            ],
        )
        self.assertTrue(all(e.usuario == self.superusuario for e in self.orden.historial.all()))

    def test_agregar_prenda_y_servicio_quedan_en_el_historial(self):
        camisa = TipoPrenda.objects.create(nombre="Camisa")
        tarifa = Tarifa.objects.create(
            tipo_prenda=camisa,
            servicio=Servicio.objects.create(nombre="Lavado"),
            valor=Decimal("8000"),
            plazo_entrega_dias=2,
            vigente_desde=date(2026, 1, 1),
        )
        self.editar_orden(
            **{"prendas-TOTAL_FORMS": "1", "prendas-0-tipo_prenda": camisa.pk, "prendas-0-cantidad": "2"}
        )
        prenda = self.orden.prendas.get()
        self.guardar(
            f"/admin/ordenes/prenda/{prenda.pk}/change/",
            **{"servicios-TOTAL_FORMS": "1", "servicios-0-tarifa": tarifa.pk, "servicios-0-valor_aplicado": "8000"},
        )

        self.assertEqual(
            list(self.orden.historial.values_list("tipo_evento", flat=True)),
            [Evento.PRENDA_AGREGADA, Evento.SERVICIO_AGREGADO],
        )

    def test_el_admin_no_permite_editar_ni_borrar_registros(self):
        evento = registrar_evento(self.orden, Evento.CREACION, self.superusuario, "original")
        base = f"/admin/ordenes/historialorden/{evento.pk}"

        self.assertEqual(self.client.post(f"{base}/change/", {"detalle": "x"}).status_code, 403)
        self.assertEqual(self.client.post(f"{base}/delete/", {"post": "yes"}).status_code, 403)
        evento.refresh_from_db()
        self.assertEqual(evento.detalle, "original")


class CatalogoDePruebaMixin:
    def crear_catalogo(self):
        self.recepcionista = User.objects.create_user(
            username="recepcion", password="x", rol=User.Rol.RECEPCIONISTA
        )
        self.cliente = Cliente.objects.create(
            documento="1090123456", nombre_completo="Ana Gomez", telefono="3001112233"
        )
        self.camisa = TipoPrenda.objects.create(nombre="Camisa")
        self.pantalon = TipoPrenda.objects.create(nombre="Pantalon")
        self.lavado = Servicio.objects.create(nombre="Lavado")
        self.planchado = Servicio.objects.create(nombre="Planchado")
        self.tarifa(self.camisa, self.lavado, "4000", Tarifa.UnidadCobro.KILO)
        self.tarifa(self.camisa, self.planchado, "2000", Tarifa.UnidadCobro.PRENDA)

    def tarifa(self, tipo_prenda, servicio, valor, unidad, **vigencia):
        vigencia.setdefault("vigente_desde", date(2020, 1, 1))
        return Tarifa.objects.create(
            tipo_prenda=tipo_prenda,
            servicio=servicio,
            valor=Decimal(valor),
            unidad_cobro=unidad,
            plazo_entrega_dias=1,
            **vigencia,
        )

    def prenda(self, *servicios, tipo=None, **extra):
        datos = {
            "tipo_prenda": (tipo or self.camisa).pk,
            "cantidad": 3,
            "peso": "2.5",
            "servicios": [s.pk for s in servicios],
        }
        datos.update(extra)
        return datos

    def registrar(self, *prendas):
        return self.client.post(
            "/api/ordenes",
            {"cliente": self.cliente.pk, "prendas": list(prendas)},
            format="json",
        )


class RegistrarOrdenApiTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)

    def test_registra_la_orden_en_espera_con_valor_abono_duracion_e_historial(self):
        response = self.registrar(self.prenda(self.lavado, self.planchado, color="azul"))

        self.assertEqual(response.status_code, 201, response.json())
        datos = response.json()
        self.assertTrue(datos["codigo"].startswith("SW-"))
        self.assertEqual(datos["estado"], Orden.Estado.EN_ESPERA)
        self.assertEqual(datos["estado_pago"], Orden.EstadoPago.PENDIENTE)
        # Lavado: 4000 x 2,5 kg. Planchado: 2000 x 3 prendas.
        self.assertEqual(Decimal(datos["valor_total"]), Decimal("16000"))
        self.assertEqual(Decimal(datos["abono_requerido"]), Decimal("4800"))
        self.assertEqual(datos["duracion_estimada_dias"], 2)
        self.assertIsNone(datos["fecha_estimada_entrega"])
        self.assertEqual(datos["detalle_prendas"][0]["color"], "azul")
        orden = Orden.objects.get()
        self.assertEqual(
            list(orden.historial.values_list("tipo_evento", flat=True)), [Evento.CREACION]
        )

    def test_el_abono_requerido_se_redondea_hacia_arriba(self):
        self.tarifa(self.pantalon, self.planchado, "3335", Tarifa.UnidadCobro.PRENDA)

        response = self.registrar(self.prenda(self.planchado, tipo=self.pantalon, cantidad=1))

        self.assertEqual(Decimal(response.json()["abono_requerido"]), Decimal("1001"))

    def test_rechaza_una_orden_sin_prendas(self):
        for cuerpo in ({"cliente": self.cliente.pk, "prendas": []}, {"cliente": self.cliente.pk}):
            response = self.client.post("/api/ordenes", cuerpo, format="json")

            self.assertEqual(response.status_code, 400)
            self.assertIn("al menos una prenda", str(response.json()["prendas"]))
        self.assertFalse(Orden.objects.exists())

    def test_rechaza_una_prenda_sin_servicios(self):
        response = self.registrar(self.prenda())

        self.assertEqual(response.status_code, 400)

    def test_rechaza_una_combinacion_sin_tarifa_vigente(self):
        self.tarifa(
            self.pantalon,
            self.lavado,
            "5000",
            Tarifa.UnidadCobro.KILO,
            vigente_hasta=date(2021, 1, 1),
        )

        response = self.registrar(self.prenda(self.lavado, tipo=self.pantalon))

        self.assertEqual(response.status_code, 400)
        self.assertIn("No hay tarifa vigente", str(response.json()))
        self.assertFalse(Orden.objects.exists())

    def test_el_peso_es_obligatorio_si_algun_servicio_se_cobra_por_kilo(self):
        sin_peso = self.registrar(self.prenda(self.lavado, peso=None))
        por_prenda = self.registrar(self.prenda(self.planchado, peso=None))

        self.assertEqual(sin_peso.status_code, 400)
        self.assertIn("peso", str(sin_peso.json()))
        self.assertEqual(por_prenda.status_code, 201)

    def test_aplica_solo_la_regla_de_descuento_que_mas_descuenta(self):
        self.tarifa(self.pantalon, self.planchado, "27000", Tarifa.UnidadCobro.PRENDA)
        regla = {"activa": True, "vigente_desde": date(2020, 1, 1)}
        ReglaDescuento.objects.create(nombre="10%", tipo="porcentaje", valor=10, **regla)
        ReglaDescuento.objects.create(nombre="Fijo", tipo="monto_fijo", valor=1000, **regla)

        response = self.registrar(self.prenda(self.planchado, tipo=self.pantalon, cantidad=1))

        self.assertEqual(Decimal(response.json()["descuento"]), Decimal("2700"))
        self.assertEqual(Decimal(response.json()["valor_total"]), Decimal("24300"))

    def test_sin_regla_aplicable_el_descuento_es_cero(self):
        ReglaDescuento.objects.create(
            nombre="Inactiva", tipo="porcentaje", valor=50, activa=False,
            vigente_desde=date(2020, 1, 1),
        )
        ReglaDescuento.objects.create(
            nombre="Vencida", tipo="porcentaje", valor=50,
            vigente_desde=date(2020, 1, 1), vigente_hasta=date(2021, 1, 1),
        )
        ReglaDescuento.objects.create(
            nombre="Solo VIP", tipo="porcentaje", valor=50,
            clasificacion_cliente=Cliente.Clasificacion.VIP, vigente_desde=date(2020, 1, 1),
        )

        response = self.registrar(self.prenda(self.planchado))

        self.assertEqual(Decimal(response.json()["descuento"]), Decimal("0"))
        self.assertEqual(Decimal(response.json()["valor_total"]), Decimal("6000"))

    def test_el_operario_no_registra_ordenes(self):
        operario = User.objects.create_user(username="op", password="x", rol=User.Rol.OPERARIO)
        self.client.force_authenticate(operario)

        self.assertEqual(self.registrar(self.prenda(self.planchado)).status_code, 403)

    def test_si_una_prenda_es_invalida_no_se_guarda_nada(self):
        response = self.registrar(
            self.prenda(self.planchado), self.prenda(self.lavado, tipo=self.pantalon)
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Orden.objects.exists())
        self.assertFalse(Prenda.objects.exists())

    def test_cambiar_la_tarifa_despues_no_altera_la_orden(self):
        self.registrar(self.prenda(self.planchado))
        Tarifa.objects.filter(servicio=self.planchado).update(valor=Decimal("9999"))

        self.assertEqual(Orden.objects.get().valor_total, Decimal("6000"))


class AgregarLineasApiTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        self.registrar(self.prenda(self.planchado))
        self.orden = Orden.objects.get()

    def agregar_prenda(self, *servicios, **extra):
        return self.client.post(
            f"/api/ordenes/{self.orden.pk}/prendas", self.prenda(*servicios, **extra), format="json"
        )

    def agregar_servicio(self, servicio):
        prenda = self.orden.prendas.first()
        return self.client.post(
            f"/api/ordenes/{self.orden.pk}/prendas/{prenda.pk}/servicios",
            {"servicio": servicio.pk},
            format="json",
        )

    def test_agregar_una_prenda_recalcula_total_abono_y_duracion(self):
        response = self.agregar_prenda(self.lavado)

        self.assertEqual(response.status_code, 201, response.json())
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.valor_total, Decimal("16000"))
        self.assertEqual(self.orden.abono_requerido, Decimal("4800"))
        self.assertEqual(self.orden.duracion_estimada_dias, 2)
        self.assertEqual(self.orden.historial.last().tipo_evento, Evento.PRENDA_AGREGADA)

    def test_agregar_un_servicio_a_una_prenda_recalcula_y_queda_en_el_historial(self):
        response = self.agregar_servicio(self.lavado)

        self.assertEqual(response.status_code, 201, response.json())
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.valor_total, Decimal("16000"))
        self.assertEqual(self.orden.historial.last().tipo_evento, Evento.SERVICIO_AGREGADO)

    def test_no_repite_un_servicio_en_la_misma_prenda(self):
        self.assertEqual(self.agregar_servicio(self.planchado).status_code, 400)

    def test_con_el_abono_ya_alcanzado_no_se_pide_otro_y_se_recalcula_la_fecha(self):
        # Viernes; la orden queda "Recibida" ese dia.
        Orden.objects.filter(pk=self.orden.pk).update(
            estado=Orden.Estado.RECIBIDA,
            abono_alcanzado_en=date(2026, 10, 9),
            abono_requerido=Decimal("1800"),
        )

        self.agregar_servicio(self.lavado)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.valor_total, Decimal("16000"))
        self.assertEqual(self.orden.abono_requerido, Decimal("1800"))
        # Dos servicios = 2 dias habiles: sabado y, saltando el domingo, lunes.
        self.assertEqual(self.orden.fecha_estimada_entrega, date(2026, 10, 12))

    def test_desde_en_proceso_no_se_agregan_prendas_ni_servicios(self):
        Orden.objects.filter(pk=self.orden.pk).update(estado=Orden.Estado.EN_PROCESO)

        self.assertEqual(self.agregar_prenda(self.planchado).status_code, 400)
        self.assertEqual(self.agregar_servicio(self.lavado).status_code, 400)
        self.assertEqual(self.orden.prendas.count(), 1)


class DuracionEstimadaTests(TestCase):
    def test_un_dia_base_mas_medio_dia_por_servicio_adicional_redondeado_hacia_arriba(self):
        self.assertEqual(
            [duracion_estimada_dias(n) for n in (1, 2, 3, 4)], [1, 2, 2, 3]
        )

    @override_settings(ORDEN_DURACION_POR_SERVICIO_ADICIONAL=Decimal("1"))
    def test_los_valores_son_configurables(self):
        self.assertEqual(duracion_estimada_dias(3), 3)

    def test_cuenta_de_lunes_a_sabado_sin_domingos(self):
        sabado = date(2026, 10, 10)
        self.assertEqual(sumar_dias_habiles(sabado, 1), date(2026, 10, 12))
        self.assertEqual(sumar_dias_habiles(date(2026, 10, 5), 5), sabado)

