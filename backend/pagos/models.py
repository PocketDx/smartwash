from django.core.exceptions import PermissionDenied
from django.db import models

from core.models import ModeloConAutoria
from ordenes.models import Orden

MENSAJE_PAGO_INMUTABLE = "Un pago registrado no se puede modificar ni eliminar."


class PagoQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionDenied(MENSAJE_PAGO_INMUTABLE)

    def delete(self):
        raise PermissionDenied(MENSAJE_PAGO_INMUTABLE)


class Pago(ModeloConAutoria):
    class Metodo(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TRANSFERENCIA = "transferencia", "Transferencia"
        TARJETA = "tarjeta", "Tarjeta"

    orden = models.ForeignKey(Orden, on_delete=models.PROTECT, related_name="pagos")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=Metodo.choices)

    objects = PagoQuerySet.as_manager()

    class Meta:
        ordering = ("creado_en", "id")
        constraints = [
            models.CheckConstraint(condition=models.Q(monto__gt=0), name="pago_monto_positivo"),
        ]

    def __str__(self):
        return f"{self.orden.codigo} · ${self.monto} ({self.get_metodo_display()})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied(MENSAJE_PAGO_INMUTABLE)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied(MENSAJE_PAGO_INMUTABLE)
