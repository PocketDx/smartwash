from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Cliente


class ClienteTests(TestCase):
    def test_no_admite_dos_clientes_con_el_mismo_documento(self):
        """HU05: el documento de identidad es unico por cliente."""
        Cliente.objects.create(documento="1090123456", nombres="Ana")
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(documento="1090123456", nombres="Otro")

    def test_el_mismo_numero_con_otro_tipo_de_documento_si_es_otro_cliente(self):
        Cliente.objects.create(
            documento="900123456",
            tipo_documento=Cliente.TipoDocumento.CEDULA_CIUDADANIA,
            nombres="Ana",
        )
        with transaction.atomic():
            Cliente.objects.create(
                documento="900123456",
                tipo_documento=Cliente.TipoDocumento.NIT,
                nombres="Lavanderia SAS",
            )
        self.assertEqual(Cliente.objects.count(), 2)
