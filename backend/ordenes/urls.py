from django.urls import path

from .views import (
    AgregarPrendaView,
    AgregarServicioView,
    CambiarEstadoView,
    HistorialOrdenView,
    OrdenDetailView,
    OrdenListCreateView,
    RegistrarEntregaView,
)

urlpatterns = [
    path("ordenes", OrdenListCreateView.as_view(), name="ordenes"),
    path("ordenes/<int:pk>", OrdenDetailView.as_view(), name="orden-detalle"),
    path("ordenes/<int:pk>/prendas", AgregarPrendaView.as_view(), name="orden-prendas"),
    path(
        "ordenes/<int:pk>/prendas/<int:prenda_pk>/servicios",
        AgregarServicioView.as_view(),
        name="orden-prenda-servicios",
    ),
    path("ordenes/<int:pk>/entrega", RegistrarEntregaView.as_view(), name="orden-entrega"),
    path("ordenes/<int:pk>/estado", CambiarEstadoView.as_view(), name="orden-estado"),
    path("ordenes/<int:pk>/historial", HistorialOrdenView.as_view(), name="orden-historial"),
]
