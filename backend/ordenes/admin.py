from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Orden, OrdenServicio, Prenda


class PrendaInline(admin.TabularInline):
    model = Prenda
    extra = 0


class OrdenServicioInline(admin.TabularInline):
    model = OrdenServicio
    extra = 0


@admin.register(Orden)
class OrdenAdmin(AutoriaAdminMixin):
    list_display = (
        "codigo",
        "cliente",
        "estado",
        "estado_pago",
        "operario",
        "valor_total",
    )
    list_filter = ("estado", "estado_pago", "operario")
    search_fields = ("codigo", "cliente__documento", "cliente__nombre_completo")
    inlines = [PrendaInline]


@admin.register(Prenda)
class PrendaAdmin(AutoriaAdminMixin):
    list_display = ("orden", "tipo_prenda", "cantidad")
    list_filter = ("tipo_prenda",)
    inlines = [OrdenServicioInline]
