from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Orden, Prenda


class PrendaInline(admin.TabularInline):
    model = Prenda
    extra = 0


@admin.register(Orden)
class OrdenAdmin(AutoriaAdminMixin):
    list_display = ("codigo", "cliente", "estado", "operario", "recibida_en", "total")
    list_filter = ("estado", "operario")
    search_fields = ("codigo", "cliente__documento", "cliente__nombres")
    inlines = [PrendaInline]
