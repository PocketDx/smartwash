from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

ANTES = [("catalogo", "0003_material"), ("ordenes", "0004_prenda_material")]
DESPUES = [("catalogo", "0005_quitar_material_de_tipoprenda")]


def ULTIMAS():
    return MigrationExecutor(connection).loader.graph.leaf_nodes()


class UnificarTiposPorMaterialTests(TransactionTestCase):
    """Corre la migracion de datos sobre una base armada con el esquema anterior."""

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def setUp(self):
        antes = self.migrar(ANTES)
        self.User = antes.get_model("accounts", "User")
        self.Tipo = antes.get_model("catalogo", "TipoPrenda")
        self.Servicio = antes.get_model("catalogo", "Servicio")
        self.Tarifa = antes.get_model("catalogo", "Tarifa")
        self.Orden = antes.get_model("ordenes", "Orden")
        self.Prenda = antes.get_model("ordenes", "Prenda")
        self.Linea = antes.get_model("ordenes", "OrdenServicio")
        self.Cliente = antes.get_model("clientes", "Cliente")
        self.lavado = self.Servicio.objects.create(nombre="Lavado")
        self.planchado = self.Servicio.objects.create(nombre="Planchado")

    def tearDown(self):
        self.migrar(ULTIMAS())

    def tarifa(self, tipo, servicio, valor, **extra):
        datos = dict(
            unidad_cobro="prenda", plazo_entrega_dias=2, vigente_desde=date(2026, 1, 1), valor=Decimal(valor)
        )
        datos.update(extra)
        return self.Tarifa.objects.create(tipo_prenda=tipo, servicio=servicio, **datos)

    def orden_con(self, *prendas):
        recepcion = self.User.objects.create(username="r", password="x", rol="recepcionista")
        cliente = self.Cliente.objects.create(documento="1", nombre_completo="Ana", telefono="1")
        orden = self.Orden.objects.create(codigo="X-1", cliente=cliente, recepcionista=recepcion)
        return [self.Prenda.objects.create(orden=orden, tipo_prenda=t) for t in prendas]

    def test_une_los_tipos_repetidos_y_conserva_prendas_tarifas_y_cobros(self):
        algodon = self.Tipo.objects.create(nombre="Camisa (Algodon)", material="Algodon")
        jean = self.Tipo.objects.create(nombre="camisa", material=" Jean ")
        pantalon = self.Tipo.objects.create(nombre="Pantalon", material="")
        self.tarifa(algodon, self.lavado, "3000")
        tarifa_jean = self.tarifa(jean, self.lavado, "3000", vigente_desde=date(2025, 6, 1))
        self.tarifa(jean, self.planchado, "2000")
        cerrada = self.tarifa(
            jean, self.lavado, "2500", vigente_desde=date(2024, 1, 1), vigente_hasta=date(2025, 6, 1)
        )
        p_algodon, p_jean, p_pantalon = self.orden_con(algodon, jean, pantalon)
        linea = self.Linea.objects.create(prenda=p_jean, tarifa=tarifa_jean, valor_aplicado=Decimal("3000"))

        despues = self.migrar(DESPUES)

        Tipo, Tarifa = despues.get_model("catalogo", "TipoPrenda"), despues.get_model("catalogo", "Tarifa")
        Prenda, Linea = despues.get_model("ordenes", "Prenda"), despues.get_model("ordenes", "OrdenServicio")
        self.assertEqual(sorted(Tipo.objects.values_list("nombre", flat=True)), ["Camisa", "Pantalon"])
        camisa = Tipo.objects.get(nombre="Camisa")
        self.assertEqual(
            sorted(despues.get_model("catalogo", "Material").objects.values_list("nombre", flat=True)),
            ["Algodon", "Jean"],
        )
        self.assertEqual(Prenda.objects.get(pk=p_algodon.pk).material.nombre, "Algodon")
        self.assertEqual(Prenda.objects.get(pk=p_jean.pk).material.nombre, "Jean")
        self.assertIsNone(Prenda.objects.get(pk=p_pantalon.pk).material)
        self.assertEqual(Prenda.objects.filter(tipo_prenda=camisa).count(), 2)
        # La tarifa vigente repetida queda una sola, desde la fecha mas antigua,
        # y el cobro ya registrado apunta a ella.
        vigente = Tarifa.objects.get(tipo_prenda=camisa, servicio_id=self.lavado.pk, vigente_hasta=None)
        self.assertEqual(vigente.vigente_desde, date(2025, 6, 1))
        self.assertEqual(Linea.objects.get(pk=linea.pk).tarifa_id, vigente.pk)
        self.assertEqual(Linea.objects.get(pk=linea.pk).valor_aplicado, Decimal("3000"))
        self.assertTrue(Tarifa.objects.filter(pk=cerrada.pk, tipo_prenda=camisa).exists())
        self.assertEqual(Tarifa.objects.filter(tipo_prenda=camisa).count(), 3)

    def test_se_detiene_si_las_tarifas_vigentes_del_mismo_servicio_difieren(self):
        a = self.Tipo.objects.create(nombre="Camisa", material="Algodon")
        b = self.Tipo.objects.create(nombre="camisa", material="Jean")
        self.tarifa(a, self.lavado, "3000")
        self.tarifa(b, self.lavado, "3500")

        with self.assertRaisesMessage(RuntimeError, "No se puede unificar"):
            self.migrar(DESPUES)

        self.assertEqual(self.Tipo.objects.count(), 2)
        self.assertEqual(self.Tarifa.objects.count(), 2)
        # El tearDown vuelve a migrar hacia adelante: sin el conflicto.
        self.Tarifa.objects.all().delete()


class TarifasPorServicioTests(TransactionTestCase):
    """Cada tarifa anterior queda como excepcion por tipo y los materiales en "Facil"."""

    ANTES = [("catalogo", "0005_quitar_material_de_tipoprenda"), ("ordenes", "0004_prenda_material")]

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def setUp(self):
        antes = self.migrar(self.ANTES)
        Tipo = antes.get_model("catalogo", "TipoPrenda")
        Servicio = antes.get_model("catalogo", "Servicio")
        self.Tarifa = antes.get_model("catalogo", "Tarifa")
        Material = antes.get_model("catalogo", "Material")
        camisa = Tipo.objects.create(nombre="Camisa")
        lavado = Servicio.objects.create(nombre="Lavado")
        planchado = Servicio.objects.create(nombre="Planchado")
        base = dict(plazo_entrega_dias=2, vigente_desde=date(2026, 1, 1))
        self.por_kilo = self.Tarifa.objects.create(
            tipo_prenda=camisa, servicio=lavado, valor=Decimal("4000"), unidad_cobro="kilo", **base
        )
        self.por_prenda = self.Tarifa.objects.create(
            tipo_prenda=camisa, servicio=planchado, valor=Decimal("2000"), unidad_cobro="prenda", **base
        )
        self.cerrada = self.Tarifa.objects.create(
            tipo_prenda=camisa,
            servicio=planchado,
            valor=Decimal("1500"),
            unidad_cobro="prenda",
            plazo_entrega_dias=2,
            vigente_desde=date(2025, 1, 1),
            vigente_hasta=date(2026, 1, 1),
        )
        Material.objects.create(nombre="Jean")
        Material.objects.create(nombre="Lana")

        User = antes.get_model("accounts", "User")
        Cliente = antes.get_model("clientes", "Cliente")
        Orden = antes.get_model("ordenes", "Orden")
        Prenda = antes.get_model("ordenes", "Prenda")
        Linea = antes.get_model("ordenes", "OrdenServicio")
        recepcion = User.objects.create(username="r", password="x", rol="recepcionista")
        cliente = Cliente.objects.create(documento="1", nombre_completo="Ana", telefono="1")
        orden = Orden.objects.create(codigo="X-1", cliente=cliente, recepcionista=recepcion)
        prenda = Prenda.objects.create(orden=orden, tipo_prenda=camisa, peso=Decimal("2.5"))
        self.linea = Linea.objects.create(prenda=prenda, tarifa=self.por_kilo, valor_aplicado=Decimal("10000"))

    def tearDown(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_las_tarifas_pasan_a_excepciones_y_los_cobros_no_cambian(self):
        despues = self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

        Tarifa = despues.get_model("catalogo", "Tarifa")
        valores = {
            t.pk: (t.valor_base, t.precio_por_kilo, t.tipo_prenda_id is not None)
            for t in Tarifa.objects.all()
        }
        self.assertEqual(valores[self.por_kilo.pk], (Decimal("0"), Decimal("4000"), True))
        self.assertEqual(valores[self.por_prenda.pk], (Decimal("2000"), Decimal("0"), True))
        self.assertEqual(valores[self.cerrada.pk], (Decimal("1500"), Decimal("0"), True))
        self.assertFalse(Tarifa.objects.filter(tipo_prenda__isnull=True).exists())

        Linea = despues.get_model("ordenes", "OrdenServicio")
        linea = Linea.objects.get(pk=self.linea.pk)
        self.assertEqual(linea.valor_aplicado, Decimal("10000"))
        self.assertIsNone(linea.valor_base)

    def test_los_materiales_existentes_quedan_en_facil_y_se_siembran_los_tres_niveles(self):
        despues = self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

        Nivel = despues.get_model("catalogo", "NivelDificultad")
        Material = despues.get_model("catalogo", "Material")
        self.assertEqual(
            {n.nombre: n.factor for n in Nivel.objects.all()},
            {"Fácil": Decimal("1.00"), "Medio": Decimal("1.30"), "Difícil": Decimal("1.60")},
        )
        self.assertEqual({m.nivel_dificultad.nombre for m in Material.objects.all()}, {"Fácil"})

    def test_se_puede_deshacer_si_todas_son_excepciones_de_un_solo_tipo_de_cobro(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

        antes = self.migrar(self.ANTES)

        Tarifa = antes.get_model("catalogo", "Tarifa")
        restauradas = {t.pk: (t.valor, t.unidad_cobro) for t in Tarifa.objects.all()}
        self.assertEqual(restauradas[self.por_kilo.pk], (Decimal("4000"), "kilo"))
        self.assertEqual(restauradas[self.por_prenda.pk], (Decimal("2000"), "prenda"))
