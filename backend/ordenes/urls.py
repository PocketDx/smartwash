from django.urls import path

from .views import HistorialOrdenView

urlpatterns = [
    path("ordenes/<int:pk>/historial", HistorialOrdenView.as_view(), name="orden-historial"),
]
