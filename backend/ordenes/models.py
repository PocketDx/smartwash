from django.conf import settings
from django.db import models

from catalogo.models import Servicio
from clientes.models import Cliente
from core.models import ModeloConAutoria


class Orden(ModeloConAutoria):
    """Orden de servicio de un cliente (EP04, EP05).

    T2 / SCRUM-51 crea solo la estructura. Quedan para sus historias:
    generar el codigo y calcular total y entrega estimada (HU09), asignar
    operario (HU10) y el flujo de estados (HU14).
    """

    class Estado(models.TextChoices):
        RECIBIDA = "recibida", "Recibida"
        EN_PROCESO = "en_proceso", "En proceso"
        LISTA = "lista", "Lista para entrega"
        ENTREGADA = "entregada", "Entregada"
        CANCELADA = "cancelada", "Cancelada"

    # HU17: el cliente consulta su orden con este codigo, asi que es publico
    # y tiene que ser unico. Generarlo es parte de HU09.
    codigo = models.CharField(max_length=20, unique=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="ordenes"
    )
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.RECIBIDA
    )
    # HU10. Null mientras no se asigne; SET_NULL para no perder la orden si
    # se desactiva al operario.
    operario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_asignadas",
    )

    recibida_en = models.DateTimeField(auto_now_add=True)
    # HU16 compara contra esta fecha para detectar ordenes retrasadas.
    entrega_estimada = models.DateTimeField(null=True, blank=True)
    entregada_en = models.DateTimeField(null=True, blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)


    class Meta:
        # Django pluriza "Orden" como "Ordens" en el admin.
        verbose_name = "orden"
        verbose_name_plural = "ordenes"
        ordering = ("-recibida_en",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0), name="orden_total_no_negativo"
            )
        ]

    def __str__(self):
        return f"{self.codigo} - {self.cliente}"


class Prenda(ModeloConAutoria):
    """Prenda incluida en una orden (EP04)."""

    orden = models.ForeignKey(
        Orden, on_delete=models.CASCADE, related_name="prendas"
    )
    # PROTECT: un servicio que ya se cobro no se puede borrar del catalogo.
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="prendas"
    )
    descripcion = models.CharField(max_length=160)
    cantidad = models.PositiveIntegerField(default=1)
    # Se copia de la tarifa al registrar la orden en vez de leerse de Tarifa:
    # si manana sube el precio, el total de esta orden no puede cambiar.
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # HU18: el operario anota lo que detecta en la prenda.
    observaciones = models.TextField(blank=True)


    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="prenda_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(valor_unitario__gte=0),
                name="prenda_valor_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion}"
