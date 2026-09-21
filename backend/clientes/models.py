from django.db import models


class Cliente(models.Model):
    """Cliente de la lavanderia (EP02).

    T2 / SCRUM-51: solo la estructura y la integridad. El CRUD es HU05.
    """

    class TipoDocumento(models.TextChoices):
        CEDULA_CIUDADANIA = "CC", "Cedula de ciudadania"
        CEDULA_EXTRANJERIA = "CE", "Cedula de extranjeria"
        PASAPORTE = "PA", "Pasaporte"
        NIT = "NIT", "NIT"

    tipo_documento = models.CharField(
        max_length=3, choices=TipoDocumento.choices, default=TipoDocumento.CEDULA_CIUDADANIA
    )
    documento = models.CharField(max_length=20)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=160, blank=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("apellidos", "nombres")
        constraints = [
            # HU05: "El documento de identidad es unico por cliente". Se valida
            # en la base y no solo en el serializer, para que dos peticiones
            # simultaneas no creen el mismo cliente dos veces.
            models.UniqueConstraint(
                fields=("tipo_documento", "documento"),
                name="cliente_documento_unico",
            )
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}".strip() or self.documento
