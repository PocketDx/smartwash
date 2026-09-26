from django.db import models

from core.models import ModeloConAutoria


class TipoPrenda(ModeloConAutoria):
    nombre = models.CharField(max_length=80, unique=True)
    material = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "tipo de prenda"
        verbose_name_plural = "tipos de prenda"

    def __str__(self):
        return self.nombre


class Servicio(ModeloConAutoria):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class Tarifa(ModeloConAutoria):
    tipo_prenda = models.ForeignKey(
        TipoPrenda, on_delete=models.PROTECT, related_name="tarifas"
    )
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="tarifas"
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    plazo_entrega_dias = models.PositiveIntegerField()
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(
        null=True, blank=True, help_text="Vacio = es la tarifa vigente."
    )

    class Meta:
        ordering = ("tipo_prenda__nombre", "servicio__nombre", "-vigente_desde")
        constraints = [
            # Una sola tarifa vigente por par, que es la regla del modelo
            # acordado. Las cerradas quedan como historico.
            models.UniqueConstraint(
                fields=("tipo_prenda", "servicio"),
                condition=models.Q(vigente_hasta__isnull=True),
                name="tarifa_vigente_unica_por_par",
            ),
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
        return f"{self.tipo_prenda} / {self.servicio}: {self.valor}"
