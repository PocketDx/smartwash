from django.shortcuts import get_object_or_404
from rest_framework import generics

from core.permissions import AdministradorORecepcionista

from .models import Orden
from .serializers import HistorialOrdenSerializer


class HistorialOrdenView(generics.ListAPIView):
    """Solo lectura: el historial no expone escritura por ningun metodo."""

    serializer_class = HistorialOrdenSerializer
    permission_classes = [AdministradorORecepcionista]

    def get_queryset(self):
        orden = get_object_or_404(Orden, pk=self.kwargs["pk"])
        return orden.historial.select_related("usuario")
