from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Material, Servicio, Tarifa, TipoPrenda


@admin.register(TipoPrenda)
class TipoPrendaAdmin(AutoriaAdminMixin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Material)
class MaterialAdmin(AutoriaAdminMixin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


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
