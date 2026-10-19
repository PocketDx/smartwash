from django.contrib import admin

from core.admin import AutoriaAdminMixin

from .models import Material, NivelDificultad, Servicio, Tarifa, TipoPrenda


@admin.register(TipoPrenda)
class TipoPrendaAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "peso_estandar")
    search_fields = ("nombre",)


@admin.register(NivelDificultad)
class NivelDificultadAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "factor")


@admin.register(Material)
class MaterialAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "nivel_dificultad")
    list_filter = ("nivel_dificultad",)
    search_fields = ("nombre",)


@admin.register(Servicio)
class ServicioAdmin(AutoriaAdminMixin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(Tarifa)
class TarifaAdmin(AutoriaAdminMixin):
    list_display = (
        "servicio",
        "tipo_prenda",
        "valor_base",
        "precio_por_kilo",
        "plazo_entrega_dias",
        "vigente_desde",
        "vigente_hasta",
    )
    list_filter = ("servicio", "tipo_prenda")
