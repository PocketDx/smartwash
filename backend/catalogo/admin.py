from django.contrib import admin

from .models import Servicio, Tarifa


class TarifaInline(admin.TabularInline):
    model = Tarifa
    extra = 0


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    inlines = [TarifaInline]


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ("servicio", "valor", "unidad", "vigente_desde", "vigente_hasta")
    list_filter = ("unidad", "servicio")
