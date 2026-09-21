from django.db import models


class Servicio(models.Model):
    """Servicio que ofrece la lavanderia: lavado, planchado, lavado en seco (EP03)."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class Tarifa(models.Model):
    """Precio vigente de un servicio (EP03).

    Un servicio tiene varias tarifas a lo largo del tiempo en vez de un solo
    precio mutable: si se sobrescribiera, cambiar el precio hoy alteraria el
    valor de las ordenes de ayer.
    """

    class Unidad(models.TextChoices):
        PRENDA = "prenda", "Por prenda"
        KILOGRAMO = "kilogramo", "Por kilogramo"

    servicio = models.ForeignKey(
        Servicio, on_delete=models.CASCADE, related_name="tarifas"
    )
    # Decimal y no float: en dinero, 0.1 + 0.2 != 0.3 arruina un total.
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    unidad = models.CharField(
        max_length=10, choices=Unidad.choices, default=Unidad.PRENDA
    )
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(
        null=True, blank=True, help_text="Vacio = sigue vigente."
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("servicio__nombre", "-vigente_desde")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gte=0), name="tarifa_valor_no_negativo"
            ),
            models.CheckConstraint(
                condition=models.Q(vigente_hasta__isnull=True)
                | models.Q(vigente_hasta__gt=models.F("vigente_desde")),
                name="tarifa_vigencia_coherente",
            ),
        ]

    def __str__(self):
        return f"{self.servicio} - {self.valor} ({self.get_unidad_display()})"
