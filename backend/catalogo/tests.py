from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from .models import Servicio, Tarifa


class TarifaTests(TestCase):
    def setUp(self):
        self.servicio = Servicio.objects.create(nombre="Lavado")

    def test_rechaza_una_tarifa_negativa(self):
        with self.assertRaises(IntegrityError):
            Tarifa.objects.create(
                servicio=self.servicio,
                valor=Decimal("-1000"),
                vigente_desde=date(2026, 1, 1),
            )

    def test_rechaza_una_vigencia_que_termina_antes_de_empezar(self):
        with self.assertRaises(IntegrityError):
            Tarifa.objects.create(
                servicio=self.servicio,
                valor=Decimal("8000"),
                vigente_desde=date(2026, 6, 1),
                vigente_hasta=date(2026, 1, 1),
            )

    def test_el_valor_se_guarda_como_decimal_exacto(self):
        """En dinero un float redondea y el total de la orden queda mal."""
        tarifa = Tarifa.objects.create(
            servicio=self.servicio,
            valor=Decimal("8500.55"),
            vigente_desde=date(2026, 1, 1),
        )
        tarifa.refresh_from_db()
        self.assertEqual(tarifa.valor, Decimal("8500.55"))
