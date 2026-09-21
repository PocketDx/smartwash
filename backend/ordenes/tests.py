from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from catalogo.models import Servicio, Tarifa
from clientes.models import Cliente

from .models import Orden, Prenda


class OrdenTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(documento="1090123456", nombres="Ana")
        self.servicio = Servicio.objects.create(nombre="Lavado")
        Tarifa.objects.create(
            servicio=self.servicio,
            valor=Decimal("8000"),
            vigente_desde=date(2026, 1, 1),
        )
        self.orden = Orden.objects.create(codigo="ORD-0001", cliente=self.cliente)

    def test_el_codigo_de_la_orden_es_unico(self):
        """HU17: el cliente consulta su orden por el codigo, no puede repetirse."""
        with self.assertRaises(IntegrityError):
            Orden.objects.create(codigo="ORD-0001", cliente=self.cliente)

    def test_no_se_puede_borrar_un_cliente_con_ordenes(self):
        with self.assertRaises(ProtectedError):
            self.cliente.delete()

    def test_no_se_puede_borrar_un_servicio_ya_cobrado(self):
        Prenda.objects.create(
            orden=self.orden,
            servicio=self.servicio,
            descripcion="Camisa blanca",
            valor_unitario=Decimal("8000"),
        )
        with self.assertRaises(ProtectedError):
            self.servicio.delete()

    def test_borrar_la_orden_borra_sus_prendas(self):
        Prenda.objects.create(
            orden=self.orden, servicio=self.servicio, descripcion="Camisa"
        )
        self.orden.delete()
        self.assertEqual(Prenda.objects.count(), 0)

    def test_rechaza_una_prenda_con_cantidad_cero(self):
        with self.assertRaises(IntegrityError):
            Prenda.objects.create(
                orden=self.orden,
                servicio=self.servicio,
                descripcion="Camisa",
                cantidad=0,
            )

    def test_la_orden_nace_recibida_y_sin_operario(self):
        self.assertEqual(self.orden.estado, Orden.Estado.RECIBIDA)
        self.assertIsNone(self.orden.operario)
