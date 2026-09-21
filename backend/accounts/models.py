from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario interno de SmartWash.

    Se define desde el scaffolding porque cambiar AUTH_USER_MODEL despues de la
    primera migracion es costoso. El rol se persiste ya (T3 / SCRUM-55) pero
    todavia NO se aplica control de acceso: eso corresponde a T8 / SCRUM-57.
    """

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        RECEPCIONISTA = "recepcionista", "Recepcionista"
        OPERARIO = "operario", "Operario"

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.OPERARIO)

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
