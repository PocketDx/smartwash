from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from clientes.models import Cliente

User = get_user_model()


class HealthTests(APITestCase):
    def test_health_is_public_and_reaches_the_database(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class AutoriaTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user(username="ana", password="x")
        self.beto = User.objects.create_user(username="beto", password="x")

    def crear_cliente(self, usuario):
        cliente = Cliente(documento="1", nombres="Cliente")
        cliente.registrar_autoria(usuario)
        cliente.save()
        return cliente

    def test_registra_quien_crea(self):
        cliente = self.crear_cliente(self.ana)

        self.assertEqual(cliente.creado_por, self.ana)
        self.assertEqual(cliente.actualizado_por, self.ana)

    def test_al_modificar_cambia_actualizado_por_pero_no_creado_por(self):
        cliente = self.crear_cliente(self.ana)

        cliente.nombres = "Otro nombre"
        cliente.registrar_autoria(self.beto)
        cliente.save()
        cliente.refresh_from_db()

        self.assertEqual(cliente.creado_por, self.ana)
        self.assertEqual(cliente.actualizado_por, self.beto)

    def test_una_escritura_sin_usuario_no_falla(self):
        self.assertIsNone(self.crear_cliente(None).creado_por)

    def test_borrar_al_autor_no_borra_lo_que_escribio(self):
        cliente = self.crear_cliente(self.ana)

        self.ana.delete()
        cliente.refresh_from_db()

        self.assertIsNone(cliente.creado_por)
        self.assertEqual(Cliente.objects.count(), 1)


# El runner de Django fuerza DEBUG=False, que es justo lo que el comando
# rechaza; estas pruebas simulan el entorno de desarrollo.
@override_settings(DEBUG=True)
class SeedUsuariosTests(TestCase):
    def test_crea_las_cuatro_cuentas_con_sus_roles(self):
        call_command("seed_usuarios", verbosity=0)

        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(
            sorted(User.objects.values_list("rol", flat=True)),
            ["administrador", "operario", "operario", "recepcionista"],
        )

    def test_las_claves_quedan_hasheadas_y_sirven_para_entrar(self):
        call_command("seed_usuarios", password="clave-de-prueba", verbosity=0)

        usuario = User.objects.get(username="recepcion")
        self.assertNotEqual(usuario.password, "clave-de-prueba")
        self.assertTrue(usuario.check_password("clave-de-prueba"))

    def test_correrlo_dos_veces_no_duplica_cuentas(self):
        call_command("seed_usuarios", verbosity=0)
        call_command("seed_usuarios", verbosity=0)

        self.assertEqual(User.objects.count(), 4)

    def test_solo_el_administrador_entra_al_django_admin(self):
        call_command("seed_usuarios", verbosity=0)

        self.assertTrue(User.objects.get(username="admin").is_staff)
        self.assertFalse(User.objects.get(username="operario1").is_staff)

    @override_settings(DEBUG=False)
    def test_se_niega_a_correr_en_produccion(self):
        with self.assertRaises(CommandError):
            call_command("seed_usuarios", verbosity=0)

        self.assertEqual(User.objects.count(), 0)
