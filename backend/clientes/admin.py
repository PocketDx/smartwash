from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(AutoriaAdminMixin):
    list_display = ("documento", "nombre_completo", "telefono", "clasificacion")
    list_filter = ("clasificacion",)
    search_fields = ("documento", "nombre_completo", "telefono", "correo")
