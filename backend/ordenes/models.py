from django.conf import settings
from django.db import models

from catalogo.models import Tarifa, TipoPrenda
from clientes.models import Cliente
from core.models import ModeloConAutoria


class Orden(ModeloConAutoria):
    class Estado(models.TextChoices):
        RECIBIDA = "Recibida", "Recibida"
        CLASIFICADA = "Clasificada", "Clasificada"
        EN_PROCESO = "En proceso", "En proceso"
        CONTROL_CALIDAD = "Control de calidad", "Control de calidad"
        LISTA = "Lista para entrega", "Lista para entrega"
        ENTREGADA = "Entregada", "Entregada"
        CANCELADA = "Cancelada", "Cancelada"
        EN_ESPERA = "En espera", "En espera"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        PARCIAL = "Parcial", "Parcial"
        PAGADA = "Pagada", "Pagada"

    # El modelo acordado expone id_orden como codigo de rastreo. Un serial es
    # enumerable: cualquiera prueba 1, 2, 3 y ve las ordenes de otros.
    codigo = models.CharField(max_length=20, unique=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="ordenes"
    )
    recepcionista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ordenes_recibidas",
    )
    # Nullable porque asignar operario es un paso posterior (HU10) y HU23 exige
    # un abono antes de hacerlo.
    operario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_asignadas",
    )
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.RECIBIDA
    )
    estado_pago = models.CharField(
        max_length=20, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )
    fecha_estimada_entrega = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    motivo_cancelacion = models.CharField(max_length=255, blank=True)
    numero_reprocesos = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "orden"
        verbose_name_plural = "ordenes"
        ordering = ("-creado_en",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_total__gte=0),
                name="orden_valor_total_no_negativo",
            )
        ]

    def __str__(self):
        return f"{self.codigo} - {self.cliente}"


class Prenda(ModeloConAutoria):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name="prendas")
    tipo_prenda = models.ForeignKey(
        TipoPrenda, on_delete=models.PROTECT, related_name="prendas"
    )
    cantidad = models.PositiveIntegerField(default=1)
    estado_inicial = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="prenda_cantidad_positiva"
            )
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.tipo_prenda}"


class OrdenServicio(ModeloConAutoria):
    prenda = models.ForeignKey(
        Prenda, on_delete=models.CASCADE, related_name="servicios"
    )
    tarifa = models.ForeignKey(
        Tarifa, on_delete=models.PROTECT, related_name="ordenes_servicio"
    )
    # Copia historica del valor de la tarifa al momento de la orden: si la
    # tarifa cambia despues, esta orden conserva lo que realmente se cobro.
    valor_aplicado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "servicio de la prenda"
        verbose_name_plural = "servicios de la prenda"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=("prenda", "tarifa"), name="orden_servicio_unico_por_prenda"
            ),
            models.CheckConstraint(
                condition=models.Q(valor_aplicado__gte=0),
                name="orden_servicio_valor_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.prenda} - {self.tarifa.servicio}"
