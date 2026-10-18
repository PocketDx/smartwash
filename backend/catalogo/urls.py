from django.urls import path

from .views import (
    MaterialDetailView,
    MaterialListCreateView,
    ServicioDetailView,
    ServicioListCreateView,
    TarifaDetailView,
    TarifaListCreateView,
    TipoPrendaDetailView,
    TipoPrendaListCreateView,
)

urlpatterns = [
    path("servicios", ServicioListCreateView.as_view(), name="servicios"),
    path("servicios/<int:pk>", ServicioDetailView.as_view(), name="servicio-detalle"),
    path("tipos-prenda", TipoPrendaListCreateView.as_view(), name="tipos-prenda"),
    path(
        "tipos-prenda/<int:pk>", TipoPrendaDetailView.as_view(), name="tipo-prenda-detalle"
    ),
    path("materiales", MaterialListCreateView.as_view(), name="materiales"),
    path("materiales/<int:pk>", MaterialDetailView.as_view(), name="material-detalle"),
    path("tarifas", TarifaListCreateView.as_view(), name="tarifas"),
    path("tarifas/<int:pk>", TarifaDetailView.as_view(), name="tarifa-detalle"),
]
