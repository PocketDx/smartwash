from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Servicio, TipoPrenda, Tarifa


@admin.register(TipoPrenda)
class TipoPrendaAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "material")
    search_fields = ("nombre", "material")


@admin.register(Servicio)
class ServicioAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(Tarifa)
class TarifaAdmin(AutoriaAdminMixin):
    list_display = (
        "tipo_prenda",
        "servicio",
        "valor",
        "plazo_entrega_dias",
        "vigente_desde",
        "vigente_hasta",
    )
    list_filter = ("servicio", "tipo_prenda")
