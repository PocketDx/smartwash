from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

User = get_user_model()

CUENTAS = [
    ("admin", "Administrador", "General", User.Rol.ADMINISTRADOR),
    ("recepcion", "Recepcion", "Mostrador", User.Rol.RECEPCIONISTA),
    ("operario1", "Operario", "Uno", User.Rol.OPERARIO),
    ("operario2", "Operario", "Dos", User.Rol.OPERARIO),
]

CLAVE_POR_DEFECTO = "smartwash123"


class Command(BaseCommand):
    help = "Crea las cuatro cuentas de prueba del equipo. Solo para desarrollo."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=CLAVE_POR_DEFECTO)

    @transaction.atomic
    def handle(self, *args, **options):
        # Clave conocida y publicada en el README: en produccion serian cuatro
        # puertas abiertas.
        if not settings.DEBUG:
            raise CommandError(
                "seed_usuarios solo corre con DEBUG=True. Son cuentas de prueba "
                "con clave conocida y no deben existir en produccion."
            )

        password = options["password"]

        for username, nombres, apellidos, rol in CUENTAS:
            usuario, creado = User.objects.get_or_create(username=username)
            usuario.first_name = nombres
            usuario.last_name = apellidos
            usuario.rol = rol
            usuario.is_staff = rol == User.Rol.ADMINISTRADOR
            usuario.is_superuser = rol == User.Rol.ADMINISTRADOR
            usuario.set_password(password)
            usuario.save()

            self.stdout.write(
                f"  {username:12} {rol:14} cuenta {'creada' if creado else 'actualizada'}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{len(CUENTAS)} cuentas listas. Clave para todas: {password}"
            )
        )
        self.stdout.write("En este sprint no hay control de acceso por rol (es T8).")
