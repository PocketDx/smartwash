from datetime import timedelta
from decimal import ROUND_CEILING, Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.crypto import get_random_string

from catalogo.models import Tarifa, TipoPrenda
from clientes.models import Cliente
from core.models import ModeloConAutoria
from fidelizacion.models import ReglaDescuento

PORCENTAJE_ABONO = Decimal("30")
# Sin 0/O ni 1/I: el codigo se dicta por telefono y se copia a mano.
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def duracion_estimada_dias(servicios_distintos):
    base = getattr(settings, "ORDEN_DURACION_BASE_DIAS", Decimal("1"))
    adicional = getattr(settings, "ORDEN_DURACION_POR_SERVICIO_ADICIONAL", Decimal("0.5"))
    if servicios_distintos == 0:
        return 0
    return int((base + adicional * (servicios_distintos - 1)).to_integral_value(ROUND_CEILING))


def sumar_dias_habiles(desde, dias):
    # Lunes (0) a sabado (5); los festivos no se descuentan.
    laborales = getattr(settings, "ORDEN_DIAS_LABORALES", {0, 1, 2, 3, 4, 5})
    fecha = desde
    while dias > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() in laborales:
            dias -= 1
    return fecha


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
    codigo = models.CharField(max_length=20, unique=True, editable=False)
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
        max_length=30, choices=Estado.choices, default=Estado.EN_ESPERA
    )
    estado_pago = models.CharField(
        max_length=20, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )
    fecha_estimada_entrega = models.DateField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    abono_requerido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duracion_estimada_dias = models.PositiveSmallIntegerField(default=0)
    # Dia en que la orden alcanzo el abono minimo y paso a "Recibida". Se
    # conserva aunque el total suba despues: el abono se exige una sola vez.
    abono_alcanzado_en = models.DateField(null=True, blank=True)
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

    def save(self, *args, **kwargs):
        if not self.codigo:
            # ponytail: sin reintento; con 32^8 combinaciones un choque es
            # improbable y el unique de la base lo detiene si ocurre.
            self.codigo = f"SW-{get_random_string(8, ALFABETO_CODIGO)}"
        super().save(*args, **kwargs)

    def tiene_abono(self):
        return self.abono_alcanzado_en is not None

    def recalcular(self):
        """Valor, abono y duracion a partir de las lineas. No guarda."""
        lineas = OrdenServicio.objects.filter(prenda__orden=self)
        self.subtotal = lineas.aggregate(total=Sum("valor_aplicado"))["total"] or Decimal("0")
        self.descuento = ReglaDescuento.objects.mayor_descuento(
            self.cliente, self.subtotal, timezone.localdate()
        )
        self.valor_total = self.subtotal - self.descuento
        if not self.tiene_abono():
            self.abono_requerido = (self.valor_total * PORCENTAJE_ABONO / 100).to_integral_value(
                ROUND_CEILING
            )
        self.duracion_estimada_dias = duracion_estimada_dias(
            lineas.values("tarifa__servicio").distinct().count()
        )
        if self.tiene_abono():
            self.fecha_estimada_entrega = sumar_dias_habiles(
                self.abono_alcanzado_en, self.duracion_estimada_dias
            )


class Prenda(ModeloConAutoria):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name="prendas")
    tipo_prenda = models.ForeignKey(
        TipoPrenda, on_delete=models.PROTECT, related_name="prendas"
    )
    cantidad = models.PositiveIntegerField(default=1)
    peso = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Kilos de la linea. Obligatorio si algun servicio se cobra por kilo.",
    )
    talla = models.CharField(max_length=20, blank=True)
    genero = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=40, blank=True)
    estado_inicial = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="prenda_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(peso__isnull=True) | models.Q(peso__gt=0),
                name="prenda_peso_positivo",
            ),
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
    # Lo cobrado por esta linea (tarifa x kilos o x prendas), congelado al
    # registrarla: si la tarifa cambia despues, la orden conserva su valor.
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


MENSAJE_HISTORIAL_INMUTABLE = "El historial de una orden no se puede modificar ni eliminar."


class HistorialOrdenQuerySet(models.QuerySet):
    # update() y delete() masivos no pasan por save()/delete() del modelo.
    def update(self, **kwargs):
        raise PermissionDenied(MENSAJE_HISTORIAL_INMUTABLE)

    def delete(self):
        raise PermissionDenied(MENSAJE_HISTORIAL_INMUTABLE)


class HistorialOrden(models.Model):
    """Registro inmutable de lo que le ocurre a una orden.

    No se crea a mano: se usa ordenes.historial.registrar_evento, dentro de la
    misma transaccion que el cambio que se registra.
    """

    class TipoEvento(models.TextChoices):
        CREACION = "creacion", "Creación"
        PAGO = "pago", "Pago"
        ASIGNACION = "asignacion", "Asignación"
        REASIGNACION = "reasignacion", "Reasignación"
        CAMBIO_ESTADO = "cambio_estado", "Cambio de estado"
        PRENDA_AGREGADA = "prenda_agregada", "Prenda agregada"
        SERVICIO_AGREGADO = "servicio_agregado", "Servicio agregado"
        ENTREGA = "entrega", "Entrega"

    # PROTECT en ambos: borrar la orden o el usuario dejaria el historial
    # incompleto o sin autor.
    orden = models.ForeignKey(
        Orden, on_delete=models.PROTECT, related_name="historial", editable=False
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eventos_de_orden",
        editable=False,
    )
    tipo_evento = models.CharField(
        max_length=30, choices=TipoEvento.choices, editable=False
    )
    detalle = models.TextField(blank=True, editable=False)
    fecha = models.DateTimeField(auto_now_add=True)

    objects = HistorialOrdenQuerySet.as_manager()

    class Meta:
        verbose_name = "evento de la orden"
        verbose_name_plural = "historial de ordenes"
        ordering = ("fecha", "id")

    def __str__(self):
        return f"{self.orden.codigo} · {self.get_tipo_evento_display()} · {self.fecha:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied(MENSAJE_HISTORIAL_INMUTABLE)
        # Una instancia nueva con el pk de un registro existente haria UPDATE.
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied(MENSAJE_HISTORIAL_INMUTABLE)
