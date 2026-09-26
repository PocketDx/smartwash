from django.db import IntegrityError
from django.test import TestCase

from .models import Cliente


class ClienteTests(TestCase):
    def test_no_admite_dos_clientes_con_el_mismo_documento(self):
        Cliente.objects.create(
            documento="1090123456", nombre_completo="Ana Gomez", telefono="3001112233"
        )
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(
                documento="1090123456", nombre_completo="Otro", telefono="3004445566"
            )

    def test_nace_clasificado_como_ocasional(self):
        cliente = Cliente.objects.create(
            documento="1090123456", nombre_completo="Ana Gomez", telefono="3001112233"
        )
        self.assertEqual(cliente.clasificacion, Cliente.Clasificacion.OCASIONAL)
