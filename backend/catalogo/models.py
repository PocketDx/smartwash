from decimal import ROUND_HALF_UP, Decimal

from django.db import models
from django.db.models import Q

from core.models import ModeloConAutoria


class TipoPrenda(ModeloConAutoria):
    nombre = models.CharField(max_length=80, unique=True)
    peso_estandar = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Kilos de una prenda tipica; prellena el peso al registrar la orden.",
    )

    class Meta:
        ordering = ("nombre",)
        verbose_name = "tipo de prenda"
        verbose_name_plural = "tipos de prenda"

    def __str__(self):
        return self.nombre


class NivelDificultad(ModeloConAutoria):
    nombre = models.CharField(max_length=80, unique=True)
    factor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Multiplica el precio de los servicios de las prendas de sus materiales.",
    )

    class Meta:
        ordering = ("factor", "nombre")
        verbose_name = "nivel de dificultad"
        verbose_name_plural = "niveles de dificultad"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(factor__gt=0), name="nivel_dificultad_factor_positivo"
            )
        ]

    def __str__(self):
        return f"{self.nombre} (x{self.factor})"


class Material(ModeloConAutoria):
    nombre = models.CharField(max_length=80, unique=True)
    nivel_dificultad = models.ForeignKey(
        NivelDificultad, on_delete=models.PROTECT, related_name="materiales"
    )

    class Meta:
        ordering = ("nombre",)
        verbose_name = "material"
        verbose_name_plural = "materiales"

    def __str__(self):
        return self.nombre


class Servicio(ModeloConAutoria):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


def redondear_a_100(valor):
    """A la centena de pesos mas cercana; el medio sube (10.550 pasa a 10.600)."""
    return (valor / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 100


class TarifaQuerySet(models.QuerySet):
    def vigentes_en(self, fecha):
        return self.filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gt=fecha), vigente_desde__lte=fecha
        )

    def aplicable(self, tipo_prenda, servicio, fecha):
        """La excepcion vigente del tipo de prenda y, si no hay, la general del servicio."""
        vigentes = self.vigentes_en(fecha).filter(servicio=servicio)
        return (
            vigentes.filter(tipo_prenda=tipo_prenda).first()
            or vigentes.filter(tipo_prenda__isnull=True).first()
        )


class Tarifa(ModeloConAutoria):
    """Precio de un servicio. Sin tipo de prenda es la tarifa general; con tipo, una
    excepcion que tiene prioridad sobre la general."""

    tipo_prenda = models.ForeignKey(
        TipoPrenda, on_delete=models.PROTECT, related_name="tarifas", null=True, blank=True
    )
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="tarifas"
    )
    valor_base = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Se cobra por cada prenda, pese lo que pese."
    )
    precio_por_kilo = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Se multiplica por el peso de la prenda en kg."
    )
    plazo_entrega_dias = models.PositiveIntegerField()
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(
        null=True, blank=True, help_text="Vacio = es la tarifa vigente."
    )

    objects = TarifaQuerySet.as_manager()

    class Meta:
        ordering = ("servicio__nombre", "tipo_prenda__nombre", "-vigente_desde")
        constraints = [
            # Las cerradas quedan como historico. NULL no cuenta como igual en
            # un indice unico, por eso la general y las excepciones van aparte.
            models.UniqueConstraint(
                fields=("servicio",),
                condition=models.Q(tipo_prenda__isnull=True, vigente_hasta__isnull=True),
                name="tarifa_general_vigente_unica",
            ),
            models.UniqueConstraint(
                fields=("tipo_prenda", "servicio"),
                condition=models.Q(tipo_prenda__isnull=False, vigente_hasta__isnull=True),
                name="tarifa_vigente_unica_por_par",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_base__gte=0) & models.Q(precio_por_kilo__gte=0),
                name="tarifa_valores_no_negativos",
            ),
            models.CheckConstraint(
                condition=models.Q(vigente_hasta__isnull=True)
                | models.Q(vigente_hasta__gt=models.F("vigente_desde")),
                name="tarifa_vigencia_coherente",
            ),
        ]

    def __str__(self):
        alcance = self.tipo_prenda or "general"
        return f"{self.servicio} / {alcance}: {self.valor_base} + {self.precio_por_kilo}/kg"
