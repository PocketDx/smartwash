from django.conf import settings
from django.db import models


class ModeloConAutoria(models.Model):
    """Base para lo que se escribe desde la aplicacion: registra quien creo y
    quien modifico por ultima vez cada fila."""

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True

    def registrar_autoria(self, usuario):
        # Opcional porque hay escrituras sin nadie detras: migraciones de datos
        # y comandos de gestion.
        if usuario is None or not usuario.is_authenticated:
            return
        if self._state.adding and self.creado_por_id is None:
            self.creado_por = usuario
        self.actualizado_por = usuario
