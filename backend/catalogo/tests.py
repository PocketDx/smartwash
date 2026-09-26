from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from .models import Servicio, TipoPrenda, Tarifa


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
