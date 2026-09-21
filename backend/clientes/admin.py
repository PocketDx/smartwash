from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("documento", "nombres", "apellidos", "telefono", "activo")
    list_filter = ("activo", "tipo_documento")
    search_fields = ("documento", "nombres", "apellidos", "telefono", "email")
