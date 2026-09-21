from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Servicio, Tarifa


class TarifaInline(admin.TabularInline):
    model = Tarifa
    extra = 0


@admin.register(Servicio)
class ServicioAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    inlines = [TarifaInline]


@admin.register(Tarifa)
class TarifaAdmin(AutoriaAdminMixin):
    list_display = ("servicio", "valor", "unidad", "vigente_desde", "vigente_hasta")
    list_filter = ("unidad", "servicio")
