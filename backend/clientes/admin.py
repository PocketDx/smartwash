from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(AutoriaAdminMixin):
    list_display = ("documento", "nombres", "apellidos", "telefono", "activo")
    list_filter = ("activo", "tipo_documento")
    search_fields = ("documento", "nombres", "apellidos", "telefono", "email")
