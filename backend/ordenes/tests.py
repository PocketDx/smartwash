from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from catalogo.models import Servicio, TipoPrenda, Tarifa
from clientes.models import Cliente
from fidelizacion.models import ReglaDescuento

from .historial import OperacionNoCompletada, operacion_sobre_orden, registrar_evento
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
        self.orden.abono_alcanzado_en = date(2026, 1, 1)
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
        # Con el abono ya registrado, para poder asignarla (HU23).
        Orden.objects.filter(pk=self.orden.pk).update(
            estado=Orden.Estado.RECIBIDA, abono_alcanzado_en=date(2026, 10, 1)
        )

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
        self.editar_orden(estado=Orden.Estado.ENTREGADA)

        self.assertEqual(
            list(self.orden.historial.values_list("tipo_evento", "detalle")),
            [
                (Evento.ASIGNACION, "sin operario → operario1"),
                (Evento.REASIGNACION, "operario1 → operario2"),
                (Evento.ENTREGA, "Recibida → Entregada"),
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


class AbonoAntesDeAsignarTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        # 16000 de valor total; abono minimo 4800.
        self.registrar(self.prenda(self.lavado, self.planchado))
        self.orden = Orden.objects.get()
        self.operario = User.objects.create_user(
            username="op", password="x", rol=User.Rol.OPERARIO
        )

    def pagar(self, monto):
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/pagos",
            {"monto": monto, "metodo": "efectivo"},
            format="json",
        )
        self.orden.refresh_from_db()

    def asignar(self):
        with operacion_sobre_orden():
            orden = Orden.objects.select_for_update().get(pk=self.orden.pk)
            orden.operario = self.operario
            orden.save()

    def test_con_el_abono_minimo_la_orden_se_puede_asignar(self):
        self.pagar("4800")

        self.asignar()

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.operario, self.operario)

    def test_sin_abono_no_se_asigna_e_indica_el_abono_requerido(self):
        self.pagar("1000")

        with self.assertRaises(ValidationError) as error:
            self.asignar()

        self.assertIn("$4800", str(error.exception.detail))
        self.assertIn("faltan $3800", str(error.exception.detail))
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.operario)

    def test_una_orden_nueva_queda_en_espera_y_no_se_puede_asignar(self):
        self.assertEqual(self.orden.estado, Orden.Estado.EN_ESPERA)
        self.assertFalse(self.orden.tiene_abono())
        with self.assertRaises(ValidationError):
            self.asignar()

    def test_al_registrar_el_abono_la_orden_pasa_a_recibida_y_se_puede_asignar(self):
        self.pagar("2000")
        self.pagar("2800")

        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.asignar()

    def test_un_abono_insuficiente_queda_parcial_y_la_orden_sigue_en_espera(self):
        self.pagar("4799")

        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PARCIAL)
        self.assertEqual(self.orden.estado, Orden.Estado.EN_ESPERA)
        with self.assertRaises(ValidationError):
            self.asignar()

    def test_si_sube_el_total_despues_del_abono_no_se_vuelve_a_exigir(self):
        self.pagar("4800")
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/prendas", self.prenda(self.lavado), format="json"
        )
        self.orden.refresh_from_db()

        self.assertEqual(self.orden.valor_total, Decimal("26000"))
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.assertTrue(self.orden.tiene_abono())
        self.asignar()

    def test_ningun_camino_guarda_una_orden_asignada_sin_abono(self):
        self.orden.operario = self.operario
        with self.assertRaises(DjangoValidationError):
            self.orden.save()
        with self.assertRaises(DjangoValidationError):
            self.orden.full_clean()

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_el_admin_muestra_el_error_y_no_asigna(self):
        admin = User.objects.create_superuser(
            username="root", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(admin)
        url = f"/admin/ordenes/orden/{self.orden.pk}/change/"
        formulario = self.client.get(url).context["adminform"].form
        datos = {c.html_name: c.value() for c in formulario if c.value() is not None}
        datos.update(
            {
                "operario": self.operario.pk,
                "prendas-TOTAL_FORMS": "0",
                "prendas-INITIAL_FORMS": "0",
                "historial-TOTAL_FORMS": "0",
                "historial-INITIAL_FORMS": "0",
            }
        )

        response = self.client.post(url, datos)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "abono minimo de $4800")
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.operario)


class EntregaExigePagoCompletoTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        # 16000 de valor total.
        self.registrar(self.prenda(self.lavado, self.planchado))
        self.orden = Orden.objects.get()

    def pagar(self, monto):
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/pagos",
            {"monto": monto, "metodo": "efectivo"},
            format="json",
        )

    def entregar(self):
        with operacion_sobre_orden():
            orden = Orden.objects.select_for_update().get(pk=self.orden.pk)
            orden.estado = Orden.Estado.ENTREGADA
            orden.save()

    def preparar_para_entrega(self):
        Orden.objects.filter(pk=self.orden.pk).update(estado=Orden.Estado.LISTA)

    def test_con_el_pago_completo_la_orden_se_entrega(self):
        self.pagar("16000")
        self.preparar_para_entrega()

        self.entregar()

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.ENTREGADA)

    def test_con_pago_incompleto_se_bloquea_e_indica_el_saldo(self):
        self.pagar("10000")
        self.preparar_para_entrega()

        with self.assertRaises(ValidationError) as error:
            self.entregar()

        self.assertIn("saldo pendiente $6000", str(error.exception.detail))
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.LISTA)

    def test_el_bloqueo_aplica_tambien_al_administrador_y_fuera_de_la_api(self):
        self.preparar_para_entrega()
        self.orden.refresh_from_db()
        self.orden.estado = Orden.Estado.ENTREGADA

        with self.assertRaises(DjangoValidationError):
            self.orden.full_clean()
        with self.assertRaises(DjangoValidationError):
            self.orden.save()

    def test_nadie_deja_el_estado_de_pago_en_pagada_sin_pago_completo(self):
        self.pagar("10000")
        self.orden.refresh_from_db()

        self.orden.estado_pago = Orden.EstadoPago.PAGADA
        self.orden.save()
        respuesta = self.client.patch(
            f"/api/ordenes/{self.orden.pk}", {"estado_pago": "Pagada"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 405)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado_pago, Orden.EstadoPago.PARCIAL)

    def test_si_sube_el_total_tras_el_abono_hay_que_pagar_la_diferencia_para_entregar(self):
        self.pagar("16000")
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/prendas", self.prenda(self.planchado), format="json"
        )
        self.preparar_para_entrega()

        with self.assertRaises(ValidationError) as error:
            self.entregar()
        self.assertIn("saldo pendiente $6000", str(error.exception.detail))

        self.pagar("6000")
        self.entregar()

    def test_si_falla_la_base_no_se_aplica_ningun_cambio(self):
        self.pagar("16000")
        self.preparar_para_entrega()

        with (
            mock.patch.object(Orden, "save", side_effect=OperationalError("sin conexion")),
            self.assertLogs("ordenes.historial", level="ERROR"),
            self.assertRaises(OperacionNoCompletada),
        ):
            self.entregar()

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.LISTA)


class RegistrarEntregaApiTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        # Dos prendas: 6000 + 10000 = 16000.
        self.registrar(self.prenda(self.planchado), self.prenda(self.lavado, color="rojo"))
        self.orden = Orden.objects.get()
        self.camisa_1, self.camisa_2 = self.orden.prendas.all()
        self.url = f"/api/ordenes/{self.orden.pk}/entrega"

    def pagar(self, monto):
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/pagos",
            {"monto": monto, "metodo": "efectivo"},
            format="json",
        )

    def lista_y_pagada(self, monto="16000"):
        self.pagar(monto)
        Orden.objects.filter(pk=self.orden.pk).update(estado=Orden.Estado.LISTA)

    def entregar(self, *verificaciones):
        if not verificaciones:
            verificaciones = (
                {"prenda": self.camisa_1.pk, "coincide": True},
                {"prenda": self.camisa_2.pk, "coincide": True},
            )
        return self.client.post(self.url, {"prendas": list(verificaciones)}, format="json")

    def test_verificadas_las_prendas_y_pagada_la_orden_queda_entregada(self):
        self.lista_y_pagada()

        response = self.entregar()

        self.assertEqual(response.status_code, 200, response.json())
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.ENTREGADA)
        self.assertIsNotNone(self.orden.fecha_entrega)
        evento = self.orden.historial.last()
        self.assertEqual(evento.tipo_evento, Evento.ENTREGA)
        self.assertEqual(evento.usuario, self.recepcionista)
        self.assertIn("2 prendas verificadas, todas coinciden", evento.detalle)

    def test_una_discrepancia_exige_observacion_y_queda_en_el_historial(self):
        self.lista_y_pagada()
        sin_observacion = self.entregar(
            {"prenda": self.camisa_1.pk, "coincide": True},
            {"prenda": self.camisa_2.pk, "coincide": False, "observacion": "  "},
        )

        self.assertEqual(sin_observacion.status_code, 400)
        self.assertIn("observacion", str(sin_observacion.json()))

        response = self.entregar(
            {"prenda": self.camisa_1.pk, "coincide": True},
            {"prenda": self.camisa_2.pk, "coincide": False, "observacion": "Mancha en el cuello"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Mancha en el cuello", self.orden.historial.last().detalle)

    def test_con_pago_incompleto_no_se_entrega_e_indica_el_saldo(self):
        self.lista_y_pagada(monto="10000")

        response = self.entregar()

        self.assertEqual(response.status_code, 400)
        self.assertIn("saldo pendiente $6000", str(response.json()))
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.LISTA)
        self.assertNotEqual(self.orden.historial.last().tipo_evento, Evento.ENTREGA)

    def test_solo_se_entrega_desde_lista_para_entrega(self):
        self.pagar("16000")

        response = self.entregar()

        self.assertEqual(response.status_code, 400)
        self.assertIn("Lista para entrega", str(response.json()))

    def test_hay_que_verificar_cada_prenda_una_sola_vez(self):
        self.lista_y_pagada()
        uno = {"prenda": self.camisa_1.pk, "coincide": True}

        for verificaciones in ((uno,), (uno, uno), (uno, {"prenda": 999, "coincide": True})):
            self.assertEqual(self.entregar(*verificaciones).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"prendas": []}, format="json").status_code, 400)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.LISTA)

    def test_el_operario_no_registra_entregas(self):
        self.lista_y_pagada()
        operario = User.objects.create_user(username="op", password="x", rol=User.Rol.OPERARIO)
        self.client.force_authenticate(operario)

        self.assertEqual(self.entregar().status_code, 403)



class CambiarEstadoApiTests(CatalogoDePruebaMixin, APITestCase):
    SECUENCIA = ("Clasificada", "En proceso", "Control de calidad", "Lista para entrega")

    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        self.registrar(self.prenda(self.planchado), self.prenda(self.lavado, color="rojo"))
        self.orden = Orden.objects.get()
        self.operario = User.objects.create_user(username="op", password="x", rol=User.Rol.OPERARIO)
        self.otro_operario = User.objects.create_user(
            username="otro", password="x", rol=User.Rol.OPERARIO
        )
        self.administrador = User.objects.create_user(
            username="admin", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.url = f"/api/ordenes/{self.orden.pk}/estado"

    def con_abono(self, operario=None):
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/pagos",
            {"monto": "4800", "metodo": "efectivo"},
            format="json",
        )
        if operario is not None:
            Orden.objects.filter(pk=self.orden.pk).update(operario=operario)

    def poner_estado(self, estado):
        Orden.objects.filter(pk=self.orden.pk).update(estado=estado)

    def cambiar(self, usuario, estado):
        self.client.force_authenticate(usuario)
        return self.client.post(self.url, {"estado": estado}, format="json")

    def test_la_recepcionista_clasifica_y_el_operario_asignado_recorre_el_resto(self):
        self.con_abono(self.operario)
        self.assertEqual(self.cambiar(self.recepcionista, "Clasificada").status_code, 200)
        previo = self.orden.historial.count()

        anterior = "Clasificada"
        for estado in self.SECUENCIA[1:]:
            response = self.cambiar(self.operario, estado)
            self.assertEqual(response.status_code, 200, response.json())
            evento = self.orden.historial.last()
            self.assertEqual(evento.tipo_evento, Evento.CAMBIO_ESTADO)
            self.assertEqual(evento.usuario, self.operario)
            self.assertEqual(evento.detalle, f"{anterior} → {estado}")
            anterior = estado

        self.assertEqual(self.orden.historial.count(), previo + len(self.SECUENCIA) - 1)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.LISTA)

    def test_el_operario_asignado_no_clasifica_la_orden(self):
        self.con_abono(self.operario)
        previo = self.orden.historial.count()

        self.assertEqual(self.cambiar(self.operario, "Clasificada").status_code, 403)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.assertEqual(self.orden.historial.count(), previo)

    def test_el_operario_no_cambia_ordenes_de_otro_ni_sin_asignar(self):
        self.con_abono(self.otro_operario)
        self.poner_estado(Orden.Estado.CLASIFICADA)
        previo = self.orden.historial.count()
        self.assertEqual(self.cambiar(self.operario, "En proceso").status_code, 403)

        Orden.objects.filter(pk=self.orden.pk).update(operario=None)
        self.assertEqual(self.cambiar(self.operario, "En proceso").status_code, 403)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.CLASIFICADA)
        self.assertEqual(self.orden.historial.count(), previo)

    def test_el_administrador_cambia_cualquier_orden(self):
        self.con_abono(self.otro_operario)

        response = self.cambiar(self.administrador, "Clasificada")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.orden.historial.last().usuario, self.administrador)

    def test_la_recepcionista_no_cambia_estados_posteriores_a_clasificada(self):
        self.con_abono(self.operario)
        self.poner_estado(Orden.Estado.CLASIFICADA)

        self.assertEqual(self.cambiar(self.recepcionista, "En proceso").status_code, 403)

    def test_una_orden_sin_operario_no_pasa_a_en_proceso(self):
        self.con_abono()
        self.poner_estado(Orden.Estado.CLASIFICADA)

        response = self.cambiar(self.administrador, "En proceso")

        self.assertEqual(response.status_code, 400)
        self.assertIn("operario asignado", str(response.json()))
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.CLASIFICADA)

    def test_una_orden_en_espera_no_se_mueve(self):
        response = self.cambiar(self.administrador, "Clasificada")

        self.assertEqual(response.status_code, 400)
        self.assertIn("abono minimo", str(response.json()))
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.EN_ESPERA)

    def test_no_se_saltan_pasos_ni_se_retrocede(self):
        self.con_abono(self.operario)

        salto = self.cambiar(self.administrador, "Lista para entrega")
        self.assertEqual(salto.status_code, 400)
        self.assertIn('No se puede pasar de "Recibida" a "Lista para entrega"', str(salto.json()))

        self.poner_estado(Orden.Estado.EN_PROCESO)
        self.assertEqual(self.cambiar(self.operario, "Clasificada").status_code, 400)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.EN_PROCESO)

    def test_la_entrega_no_se_hace_por_este_endpoint(self):
        self.con_abono(self.operario)
        self.poner_estado(Orden.Estado.LISTA)

        self.assertEqual(self.cambiar(self.administrador, "Entregada").status_code, 400)

    def test_un_estado_desconocido_se_rechaza(self):
        self.con_abono(self.operario)

        self.assertEqual(self.cambiar(self.operario, "Volando").status_code, 400)

    def test_el_reproceso_vuelve_a_en_proceso_las_veces_que_haga_falta(self):
        self.con_abono(self.operario)
        self.poner_estado(Orden.Estado.CONTROL_CALIDAD)

        for _ in range(2):
            self.assertEqual(self.cambiar(self.operario, "En proceso").status_code, 200)
            self.assertEqual(self.cambiar(self.operario, "Control de calidad").status_code, 200)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.numero_reprocesos, 2)
        self.assertEqual(self.orden.valor_total, Decimal("16000"))

    def test_si_falla_la_base_no_se_aplica_ningun_cambio(self):
        self.con_abono(self.operario)

        previo = self.orden.historial.count()

        with (
            mock.patch.object(Orden, "save", side_effect=OperationalError("sin conexion")),
            self.assertLogs("ordenes.historial", level="ERROR"),
        ):
            response = self.cambiar(self.recepcionista, "Clasificada")

        self.assertEqual(response.status_code, 503)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.assertEqual(self.orden.historial.count(), previo)


class AsignarOperarioApiTests(CatalogoDePruebaMixin, APITestCase):
    def setUp(self):
        self.crear_catalogo()
        self.client.force_authenticate(self.recepcionista)
        # 16000 de valor total; abono minimo 4800.
        self.registrar(self.prenda(self.lavado, self.planchado))
        self.orden = Orden.objects.get()
        self.operario = User.objects.create_user(
            username="op1", password="x", rol=User.Rol.OPERARIO, first_name="Luis"
        )
        self.otro_operario = User.objects.create_user(
            username="op2", password="x", rol=User.Rol.OPERARIO, first_name="Marta"
        )
        self.admin = User.objects.create_user(
            username="jefe", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def pagar(self, monto):
        self.client.post(
            f"/api/ordenes/{self.orden.pk}/pagos",
            {"monto": monto, "metodo": "efectivo"},
            format="json",
        )

    def asignar(self, operario):
        pk = operario.pk if isinstance(operario, User) else operario
        return self.client.post(
            f"/api/ordenes/{self.orden.pk}/asignacion", {"operario": pk}, format="json"
        )

    def eventos(self, tipo):
        return HistorialOrden.objects.filter(orden=self.orden, tipo_evento=tipo)

    def fijar_estado(self, estado):
        Orden.objects.filter(pk=self.orden.pk).update(estado=estado)

    def desactivar(self, usuario):
        usuario.is_active = False
        usuario.save()

    def test_con_abono_la_recepcionista_asigna_y_queda_en_el_historial(self):
        self.pagar("4800")

        response = self.asignar(self.operario)

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["operario"], self.operario.pk)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.operario, self.operario)
        self.assertEqual(self.orden.actualizado_por, self.recepcionista)
        evento = self.eventos(Evento.ASIGNACION).get()
        self.assertEqual(evento.usuario, self.recepcionista)
        self.assertEqual(evento.detalle, "Asignada a Luis")
        self.assertIsNotNone(evento.fecha)

    def test_el_administrador_tambien_asigna(self):
        self.pagar("4800")
        self.client.force_authenticate(self.admin)

        self.assertEqual(self.asignar(self.operario).status_code, 200)
        self.assertEqual(self.eventos(Evento.ASIGNACION).get().usuario, self.admin)

    def test_sin_abono_rechaza_e_indica_que_se_requiere(self):
        self.pagar("1000")

        response = self.asignar(self.operario)

        self.assertEqual(response.status_code, 400)
        self.assertIn("abono minimo de $4800", str(response.json()))
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.operario)
        self.assertFalse(self.eventos(Evento.ASIGNACION).exists())

    def test_no_asigna_una_orden_en_espera(self):
        self.pagar("4800")
        self.fijar_estado(Orden.Estado.EN_ESPERA)

        response = self.asignar(self.operario)

        self.assertEqual(response.status_code, 400)
        self.assertIn("En espera", str(response.json()))

    def test_no_asigna_a_un_operario_inactivo(self):
        self.pagar("4800")
        self.desactivar(self.operario)

        response = self.asignar(self.operario)

        self.assertEqual(response.status_code, 400)
        self.assertIn("operario activo", str(response.json()))

    def test_no_asigna_a_quien_no_es_operario_ni_a_ids_invalidos(self):
        self.pagar("4800")

        for invalido in (self.recepcionista, self.admin, 999999, "abc", None):
            with self.subTest(invalido=invalido):
                self.assertEqual(self.asignar(invalido).status_code, 400)
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.operario)

    def test_reasigna_en_recibida_y_en_clasificada(self):
        self.pagar("4800")
        self.asignar(self.operario)

        self.assertEqual(self.asignar(self.otro_operario).status_code, 200)
        self.fijar_estado(Orden.Estado.CLASIFICADA)
        self.assertEqual(self.asignar(self.operario).status_code, 200)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.operario, self.operario)
        detalles = list(self.eventos(Evento.REASIGNACION).values_list("detalle", flat=True))
        self.assertEqual(detalles, ["Luis → Marta", "Marta → Luis"])

    def test_reasignar_al_mismo_operario_se_rechaza_sin_ensuciar_el_historial(self):
        self.pagar("4800")
        self.asignar(self.operario)

        self.assertEqual(self.asignar(self.operario).status_code, 400)
        self.assertFalse(self.eventos(Evento.REASIGNACION).exists())

    def test_en_proceso_la_orden_queda_fija(self):
        self.pagar("4800")
        self.asignar(self.operario)
        self.fijar_estado(Orden.Estado.EN_PROCESO)

        self.assertEqual(self.asignar(self.otro_operario).status_code, 400)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.asignar(self.otro_operario).status_code, 400)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.operario, self.operario)

    def test_el_admin_reasigna_en_proceso_si_el_operario_fue_desactivado(self):
        self.pagar("4800")
        self.asignar(self.operario)
        self.fijar_estado(Orden.Estado.EN_PROCESO)
        self.desactivar(self.operario)

        self.assertEqual(self.asignar(self.otro_operario).status_code, 400)
        self.client.force_authenticate(self.admin)
        response = self.asignar(self.otro_operario)

        self.assertEqual(response.status_code, 200, response.json())
        evento = self.eventos(Evento.REASIGNACION).get()
        self.assertEqual(evento.usuario, self.admin)
        self.assertIn("desactivado", evento.detalle)

    def test_no_reasigna_una_orden_lista_entregada_o_cancelada(self):
        self.pagar("4800")
        self.asignar(self.operario)
        self.desactivar(self.operario)
        self.client.force_authenticate(self.admin)

        for estado in (Orden.Estado.LISTA, Orden.Estado.ENTREGADA, Orden.Estado.CANCELADA):
            with self.subTest(estado=estado):
                self.fijar_estado(estado)
                self.assertEqual(self.asignar(self.otro_operario).status_code, 400)

    def test_el_operario_recibe_403_al_asignar_o_reasignar(self):
        self.pagar("4800")
        self.client.force_authenticate(self.operario)
        self.assertEqual(self.asignar(self.operario).status_code, 403)

        self.client.force_authenticate(self.recepcionista)
        self.asignar(self.operario)
        self.client.force_authenticate(self.operario)
        self.assertEqual(self.asignar(self.otro_operario).status_code, 403)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.operario, self.operario)

    def test_sin_sesion_no_asigna(self):
        self.client.force_authenticate(None)

        self.assertIn(self.asignar(self.operario).status_code, (401, 403))

    def test_una_peticion_rechazada_no_deja_cambios_ni_eventos(self):
        self.pagar("4800")
        antes = HistorialOrden.objects.count()

        self.assertEqual(self.asignar(None).status_code, 400)

        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.operario)
        self.assertEqual(HistorialOrden.objects.count(), antes)

    def test_si_falla_el_historial_no_queda_la_asignacion(self):
        self.pagar("4800")

        with mock.patch("ordenes.views.registrar_evento", side_effect=OperationalError("caida")):
            response = self.asignar(self.operario)

        self.assertEqual(response.status_code, 503)
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.operario)

    def test_lista_solo_operarios_activos_para_recepcion_y_admin(self):
        User.objects.create_user(
            username="op3", password="x", rol=User.Rol.OPERARIO, is_active=False
        )

        response = self.client.get("/api/operarios")

        self.assertEqual(response.status_code, 200)
        ids = {o["id"] for o in response.json()}
        self.assertEqual(ids, {self.operario.pk, self.otro_operario.pk})
        self.client.force_authenticate(self.operario)
        self.assertEqual(self.client.get("/api/operarios").status_code, 403)

