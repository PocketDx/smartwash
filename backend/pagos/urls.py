from django.urls import path

from .views import PagoListCreateView

urlpatterns = [
    path("ordenes/<int:pk>/pagos", PagoListCreateView.as_view(), name="orden-pagos"),
]
