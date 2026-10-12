from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """Solo consulta: un pago se registra por la API, que valida el saldo y
    deja el evento en el historial."""

    list_display = ("orden", "monto", "metodo", "creado_por", "creado_en")
    list_filter = ("metodo",)
    search_fields = ("orden__codigo",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
