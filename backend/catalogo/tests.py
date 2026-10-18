from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Material, Servicio, Tarifa, TipoPrenda

User = get_user_model()


class TarifaTests(TestCase):
    def setUp(self):
        self.camisa = TipoPrenda.objects.create(nombre="Camisa")
        self.lavado = Servicio.objects.create(nombre="Lavado")

    def crear_tarifa(self, valor="8000", desde=date(2026, 1, 1), hasta=None, **extra):
        return Tarifa.objects.create(
            tipo_prenda=extra.get("tipo_prenda", self.camisa),
            servicio=extra.get("servicio", self.lavado),
            valor=Decimal(valor),
            plazo_entrega_dias=2,
            vigente_desde=desde,
            vigente_hasta=hasta,
        )

    def test_solo_admite_una_tarifa_vigente_por_tipo_de_prenda_y_servicio(self):
        self.crear_tarifa()
        with self.assertRaises(IntegrityError):
            self.crear_tarifa(valor="9000")

    def test_al_cerrar_la_vigencia_se_puede_registrar_la_nueva_tarifa(self):
        anterior = self.crear_tarifa(valor="8000")
        anterior.vigente_hasta = date(2026, 6, 1)
        anterior.save()

        self.crear_tarifa(valor="9000", desde=date(2026, 6, 1))

        self.assertEqual(Tarifa.objects.count(), 2)
        self.assertEqual(Tarifa.objects.filter(vigente_hasta__isnull=True).count(), 1)

    def test_rechaza_una_tarifa_negativa(self):
        with self.assertRaises(IntegrityError):
            self.crear_tarifa(valor="-1000")

    def test_rechaza_una_vigencia_que_termina_antes_de_empezar(self):
        with self.assertRaises(IntegrityError):
            self.crear_tarifa(desde=date(2026, 6, 1), hasta=date(2026, 1, 1))

    def test_el_valor_se_guarda_como_decimal_exacto(self):
        tarifa = self.crear_tarifa(valor="8500.55")
        tarifa.refresh_from_db()
        self.assertEqual(tarifa.valor, Decimal("8500.55"))


class CatalogoApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="smartwash123", rol=User.Rol.ADMINISTRADOR
        )
        self.client.login(username="admin", password="smartwash123")
        self.camisa = TipoPrenda.objects.create(nombre="Camisa")
        self.lavado = Servicio.objects.create(nombre="Lavado")

    def datos_tarifa(self, **extra):
        datos = {
            "tipo_prenda": self.camisa.pk,
            "servicio": self.lavado.pk,
            "valor": "8000.00",
            "plazo_entrega_dias": 2,
            "vigente_desde": "2026-01-01",
        }
        datos.update(extra)
        return datos

    def test_crea_un_servicio_y_registra_quien_lo_creo(self):
        response = self.client.post(
            "/api/catalogo/servicios", {"nombre": "Planchado", "descripcion": "A vapor"}
        )
        self.assertEqual(response.status_code, 201)
        servicio = Servicio.objects.get(nombre="Planchado")
        self.assertEqual(servicio.creado_por, self.admin)

    def test_edita_un_servicio_existente(self):
        response = self.client.patch(
            f"/api/catalogo/servicios/{self.lavado.pk}",
            {"descripcion": "Lavado en agua"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.lavado.refresh_from_db()
        self.assertEqual(self.lavado.descripcion, "Lavado en agua")
        self.assertEqual(self.lavado.actualizado_por, self.admin)

    def test_rechaza_un_servicio_duplicado_sin_importar_mayusculas(self):
        response = self.client.post("/api/catalogo/servicios", {"nombre": " lavado "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("nombre", response.json())
        self.assertEqual(Servicio.objects.count(), 1)

    def test_crea_un_tipo_de_prenda(self):
        response = self.client.post(
            "/api/catalogo/tipos-prenda", {"nombre": "Cobija"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"id": TipoPrenda.objects.get(nombre="Cobija").pk, "nombre": "Cobija"})

    def test_crea_y_edita_un_material_con_autoria(self):
        creado = self.client.post("/api/catalogo/materiales", {"nombre": "Lana"})
        self.assertEqual(creado.status_code, 201)
        material = Material.objects.get()
        self.assertEqual(material.creado_por, self.admin)

        editado = self.client.patch(
            f"/api/catalogo/materiales/{material.pk}", {"nombre": "Seda"}, content_type="application/json"
        )
        self.assertEqual(editado.status_code, 200)
        material.refresh_from_db()
        self.assertEqual(material.nombre, "Seda")

    def test_rechaza_un_material_repetido_sin_importar_mayusculas(self):
        Material.objects.create(nombre="Algodon")
        response = self.client.post("/api/catalogo/materiales", {"nombre": " algodon "})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Material.objects.count(), 1)

    def test_cualquier_sesion_lista_materiales_y_solo_el_administrador_escribe(self):
        Material.objects.create(nombre="Jean")
        for rol in (User.Rol.RECEPCIONISTA, User.Rol.OPERARIO):
            usuario = User.objects.create_user(username=f"u-{rol}", password="x", rol=rol)
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get("/api/catalogo/materiales").status_code, 200)
            self.assertEqual(self.client.post("/api/catalogo/materiales", {"nombre": "Lino"}).status_code, 403)
            self.assertEqual(
                self.client.post("/api/catalogo/tipos-prenda", {"nombre": "Saco"}).status_code, 403
            )
        self.assertEqual(Material.objects.count(), 1)

    def test_crea_una_tarifa_para_un_par_prenda_servicio(self):
        response = self.client.post("/api/catalogo/tarifas", self.datos_tarifa())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["servicio_nombre"], "Lavado")
        tarifa = Tarifa.objects.get()
        self.assertEqual(tarifa.valor, Decimal("8000.00"))
        self.assertEqual(tarifa.creado_por, self.admin)

    def test_rechaza_una_tarifa_negativa(self):
        response = self.client.post("/api/catalogo/tarifas", self.datos_tarifa(valor="-1"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Tarifa.objects.exists())

    def test_rechaza_una_tarifa_vacia(self):
        response = self.client.post("/api/catalogo/tarifas", self.datos_tarifa(valor=""))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Tarifa.objects.exists())

    def test_una_tarifa_nueva_cierra_la_vigente_y_conserva_el_historico(self):
        self.client.post("/api/catalogo/tarifas", self.datos_tarifa())
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(valor="9000.00", vigente_desde="2026-06-01"),
        )
        self.assertEqual(response.status_code, 201)
        anterior = Tarifa.objects.get(valor=Decimal("8000.00"))
        self.assertEqual(anterior.vigente_hasta, date(2026, 6, 1))
        vigentes = self.client.get("/api/catalogo/tarifas?vigentes=1").json()
        self.assertEqual([t["valor"] for t in vigentes], ["9000.00"])

    def test_una_tarifa_nueva_no_puede_empezar_antes_que_la_vigente(self):
        self.client.post("/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-06-01"))
        response = self.client.post(
            "/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-01-01")
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tarifa.objects.count(), 1)
        self.assertIsNone(Tarifa.objects.get().vigente_hasta)

    def test_rechaza_una_tarifa_cerrada_que_se_cruza_con_la_vigente(self):
        self.client.post("/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-06-01"))
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-07-01", vigente_hasta="2026-08-01"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("vigente_desde", response.json())
        self.assertEqual(Tarifa.objects.count(), 1)
        self.assertIsNone(Tarifa.objects.get().vigente_hasta)

    def test_rechaza_una_tarifa_cerrada_que_se_cruza_con_una_historica(self):
        self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-01-01", vigente_hasta="2026-03-01"),
        )
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-02-01", vigente_hasta="2026-04-01"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tarifa.objects.count(), 1)

    def test_rechaza_una_tarifa_cerrada_que_envuelve_a_otra(self):
        self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-02-01", vigente_hasta="2026-03-01"),
        )
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-01-01", vigente_hasta="2026-06-01"),
        )
        self.assertEqual(response.status_code, 400)

    def test_acepta_tarifas_cerradas_contiguas(self):
        self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-01-01", vigente_hasta="2026-03-01"),
        )
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-03-01", vigente_hasta="2026-04-01"),
        )
        self.assertEqual(response.status_code, 201)

    def test_acepta_una_tarifa_cerrada_anterior_a_la_vigente(self):
        self.client.post("/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-06-01"))
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-01-01", vigente_hasta="2026-06-01"),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Tarifa.objects.filter(vigente_hasta__isnull=True).count(), 1)

    def test_el_solape_solo_se_evalua_dentro_del_mismo_par_prenda_servicio(self):
        pantalon = TipoPrenda.objects.create(nombre="Pantalon")
        self.client.post("/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-06-01"))
        response = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(
                tipo_prenda=pantalon.pk, vigente_desde="2026-07-01", vigente_hasta="2026-08-01"
            ),
        )
        self.assertEqual(response.status_code, 201)

    def test_una_tarifa_nueva_abierta_no_puede_cruzarse_con_una_cerrada_posterior(self):
        Tarifa.objects.create(
            tipo_prenda=self.camisa,
            servicio=self.lavado,
            valor=Decimal("7000"),
            plazo_entrega_dias=2,
            vigente_desde=date(2026, 7, 1),
            vigente_hasta=date(2026, 8, 1),
        )
        Tarifa.objects.create(
            tipo_prenda=self.camisa,
            servicio=self.lavado,
            valor=Decimal("8000"),
            plazo_entrega_dias=2,
            vigente_desde=date(2026, 6, 1),
        )
        response = self.client.post(
            "/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-06-15")
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tarifa.objects.count(), 2)

    def test_editar_una_tarifa_no_choca_consigo_misma(self):
        tarifa_id = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-01-01", vigente_hasta="2026-03-01"),
        ).json()["id"]
        response = self.client.patch(
            f"/api/catalogo/tarifas/{tarifa_id}",
            {"valor": "8500.00", "vigente_hasta": "2026-04-01"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tarifa.objects.get(pk=tarifa_id).vigente_hasta, date(2026, 4, 1))

    def test_no_permite_extender_una_tarifa_hasta_cruzarse_con_otra(self):
        primera = self.client.post(
            "/api/catalogo/tarifas",
            self.datos_tarifa(vigente_desde="2026-01-01", vigente_hasta="2026-03-01"),
        ).json()["id"]
        self.client.post("/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-03-01"))
        response = self.client.patch(
            f"/api/catalogo/tarifas/{primera}",
            {"vigente_hasta": "2026-05-01"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tarifa.objects.get(pk=primera).vigente_hasta, date(2026, 3, 1))

    def test_no_permite_mover_una_tarifa_a_otro_servicio(self):
        tarifa_id = self.client.post("/api/catalogo/tarifas", self.datos_tarifa()).json()["id"]
        planchado = Servicio.objects.create(nombre="Planchado")
        response = self.client.patch(
            f"/api/catalogo/tarifas/{tarifa_id}",
            {"servicio": planchado.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_no_permite_reabrir_una_tarifa_si_ya_hay_otra_vigente(self):
        primera = self.client.post("/api/catalogo/tarifas", self.datos_tarifa()).json()["id"]
        self.client.post(
            "/api/catalogo/tarifas", self.datos_tarifa(vigente_desde="2026-06-01")
        )
        response = self.client.patch(
            f"/api/catalogo/tarifas/{primera}",
            {"vigente_hasta": None},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_una_edicion_rechazada_no_cambia_nada(self):
        tarifa_id = self.client.post("/api/catalogo/tarifas", self.datos_tarifa()).json()["id"]
        response = self.client.patch(
            f"/api/catalogo/tarifas/{tarifa_id}",
            {"valor": "9500.00", "plazo_entrega_dias": 0},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        tarifa = Tarifa.objects.get(pk=tarifa_id)
        self.assertEqual(tarifa.valor, Decimal("8000.00"))
        self.assertEqual(tarifa.plazo_entrega_dias, 2)

    def test_requiere_sesion_activa(self):
        self.client.logout()
        response = self.client.post("/api/catalogo/servicios", {"nombre": "Planchado"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Servicio.objects.filter(nombre="Planchado").exists())

    def test_la_tarifa_se_cobra_por_kilo_si_no_se_indica_la_unidad(self):
        response = self.client.post("/api/catalogo/tarifas", self.datos_tarifa())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["unidad_cobro"], "kilo")

    def test_crea_una_tarifa_por_prenda(self):
        response = self.client.post(
            "/api/catalogo/tarifas", self.datos_tarifa(unidad_cobro="prenda")
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Tarifa.objects.get().unidad_cobro, Tarifa.UnidadCobro.PRENDA)

    def test_rechaza_una_unidad_de_cobro_desconocida(self):
        response = self.client.post(
            "/api/catalogo/tarifas", self.datos_tarifa(unidad_cobro="metro")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("unidad_cobro", response.json())
        self.assertFalse(Tarifa.objects.exists())

    def test_cambia_la_unidad_de_cobro_de_una_tarifa_existente(self):
        tarifa_id = self.client.post("/api/catalogo/tarifas", self.datos_tarifa()).json()["id"]
        response = self.client.patch(
            f"/api/catalogo/tarifas/{tarifa_id}",
            {"unidad_cobro": "prenda"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tarifa.objects.get(pk=tarifa_id).unidad_cobro, "prenda")


class CatalogoPermisosTests(APITestCase):
    def setUp(self):
        User.objects.create_user(
            username="admin", password="smartwash123", rol=User.Rol.ADMINISTRADOR
        )
        User.objects.create_user(
            username="recepcion", password="smartwash123", rol=User.Rol.RECEPCIONISTA
        )
        self.camisa = TipoPrenda.objects.create(nombre="Camisa")
        self.lavado = Servicio.objects.create(nombre="Lavado")
        self.tarifa = Tarifa.objects.create(
            tipo_prenda=self.camisa,
            servicio=self.lavado,
            valor="8000.00",
            plazo_entrega_dias=2,
            vigente_desde="2026-01-01",
        )
        self.client.login(username="recepcion", password="smartwash123")

    def test_el_recepcionista_consulta_el_catalogo(self):
        for ruta in ("tipos-prenda", "servicios", "tarifas"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(f"/api/catalogo/{ruta}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/catalogo/tarifas/{self.tarifa.pk}").status_code, 200)

    def test_el_recepcionista_no_crea_nada_en_el_catalogo(self):
        creaciones = {
            "tipos-prenda": {"nombre": "Cobija"},
            "servicios": {"nombre": "Planchado"},
            "tarifas": {
                "tipo_prenda": self.camisa.pk,
                "servicio": self.lavado.pk,
                "valor": "9000.00",
                "plazo_entrega_dias": 2,
                "vigente_desde": "2026-06-01",
            },
        }
        for ruta, datos in creaciones.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.post(f"/api/catalogo/{ruta}", datos).status_code, 403)
        self.assertEqual(TipoPrenda.objects.count(), 1)
        self.assertEqual(Servicio.objects.count(), 1)
        self.assertEqual(Tarifa.objects.count(), 1)

    def test_el_recepcionista_no_edita_el_catalogo(self):
        ediciones = {
            f"tipos-prenda/{self.camisa.pk}": {"nombre": "Otra"},
            f"servicios/{self.lavado.pk}": {"nombre": "Otro"},
            f"tarifas/{self.tarifa.pk}": {"valor": "1.00"},
        }
        for ruta, datos in ediciones.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(
                    self.client.patch(f"/api/catalogo/{ruta}", datos, format="json").status_code, 403
                )
        self.tarifa.refresh_from_db()
        self.assertEqual(self.tarifa.valor, Decimal("8000.00"))

    def test_el_administrador_si_escribe_en_el_catalogo(self):
        self.client.login(username="admin", password="smartwash123")
        response = self.client.post("/api/catalogo/servicios", {"nombre": "Planchado"})
        self.assertEqual(response.status_code, 201)
