from rest_framework import generics

from core.permissions import SoloAdministradorEscribe

from .models import Material, Servicio, Tarifa, TipoPrenda
from .serializers import (
    MaterialSerializer,
    ServicioSerializer,
    TarifaSerializer,
    TipoPrendaSerializer,
)


class ServicioListCreateView(generics.ListCreateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer


class ServicioDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer


class TipoPrendaListCreateView(generics.ListCreateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = TipoPrenda.objects.all()
    serializer_class = TipoPrendaSerializer


class TipoPrendaDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = TipoPrenda.objects.all()
    serializer_class = TipoPrendaSerializer


class MaterialListCreateView(generics.ListCreateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer


class MaterialDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer


class TarifaListCreateView(generics.ListCreateAPIView):
    """Con ?vigentes=1 devuelve solo las tarifas que se usan para cotizar."""

    permission_classes = [SoloAdministradorEscribe]
    serializer_class = TarifaSerializer

    def get_queryset(self):
        tarifas = Tarifa.objects.select_related("tipo_prenda", "servicio")
        if self.request.query_params.get("vigentes") in ("1", "true"):
            tarifas = tarifas.filter(vigente_hasta__isnull=True)
        return tarifas


class TarifaDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [SoloAdministradorEscribe]
    queryset = Tarifa.objects.select_related("tipo_prenda", "servicio")
    serializer_class = TarifaSerializer
