from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import AdministradorORecepcionista, RecepcionEscribe

from .historial import operacion_sobre_orden, registrar_evento
from .models import HistorialOrden, Orden, Prenda
from .serializers import (
    AgregarServicioSerializer,
    AsignacionSerializer,
    CambioEstadoSerializer,
    EntregaSerializer,
    HistorialOrdenSerializer,
    OperarioSerializer,
    OrdenSerializer,
    PrendaEntradaSerializer,
    agregar_prenda,
    agregar_servicio,
    asignar_operario,
    exigir_orden_editable,
    guardar_recalculo,
    operarios_activos,
)

Evento = HistorialOrden.TipoEvento


def ordenes_con_detalle():
    return Orden.objects.select_related("cliente").prefetch_related(
        "prendas__tipo_prenda", "prendas__servicios__tarifa__servicio"
    )


class OrdenListCreateView(generics.ListCreateAPIView):
    serializer_class = OrdenSerializer
    permission_classes = [RecepcionEscribe]

    def get_queryset(self):
        return ordenes_con_detalle()


class OrdenDetailView(generics.RetrieveAPIView):
    serializer_class = OrdenSerializer

    def get_queryset(self):
        return ordenes_con_detalle()


def orden_para_editar(pk):
    # El bloqueo evita que dos recepcionistas recalculen el total a la vez.
    orden = get_object_or_404(Orden.objects.select_for_update(), pk=pk)
    exigir_orden_editable(orden)
    return orden


def respuesta_orden(orden):
    return Response(
        OrdenSerializer(ordenes_con_detalle().get(pk=orden.pk)).data,
        status=status.HTTP_201_CREATED,
    )


class AgregarPrendaView(APIView):
    permission_classes = [AdministradorORecepcionista]

    def post(self, request, pk):
        entrada = PrendaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with operacion_sobre_orden():
            orden = orden_para_editar(pk)
            prenda = agregar_prenda(orden, entrada.validated_data, request.user)
            guardar_recalculo(orden, request.user)
            registrar_evento(
                orden,
                Evento.PRENDA_AGREGADA,
                request.user,
                f"{prenda}. Nuevo total ${orden.valor_total}",
            )
        return respuesta_orden(orden)


class AgregarServicioView(APIView):
    permission_classes = [AdministradorORecepcionista]

    def post(self, request, pk, prenda_pk):
        with operacion_sobre_orden():
            orden = orden_para_editar(pk)
            prenda = get_object_or_404(Prenda, pk=prenda_pk, orden=orden)
            entrada = AgregarServicioSerializer(data=request.data, context={"prenda": prenda})
            entrada.is_valid(raise_exception=True)
            linea = agregar_servicio(prenda, entrada.validated_data["servicio"], request.user)
            guardar_recalculo(orden, request.user)
            registrar_evento(
                orden,
                Evento.SERVICIO_AGREGADO,
                request.user,
                f"{linea} (${linea.valor_aplicado}). Nuevo total ${orden.valor_total}",
            )
        return respuesta_orden(orden)


class RegistrarEntregaView(APIView):
    permission_classes = [AdministradorORecepcionista]

    def post(self, request, pk):
        entrada = EntregaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with operacion_sobre_orden():
            orden = get_object_or_404(Orden.objects.select_for_update(), pk=pk)
            if orden.estado != Orden.Estado.LISTA:
                raise serializers.ValidationError(
                    {"estado": f'La orden esta "{orden.estado}"; solo se entrega desde "Lista para entrega".'}
                )
            detalle = entrada.verificar_contra(orden)
            # save() exige el pago completo (HU24) e indica el saldo si falta.
            orden.estado = Orden.Estado.ENTREGADA
            orden.fecha_entrega = timezone.now()
            orden.registrar_autoria(request.user)
            orden.save()
            registrar_evento(
                orden, Evento.ENTREGA, request.user, f"Lista para entrega → Entregada. {detalle}"
            )
        return Response(OrdenSerializer(ordenes_con_detalle().get(pk=orden.pk)).data)


def puede_cambiar_estado(usuario, orden):
    if usuario.rol == User.Rol.ADMINISTRADOR:
        return True
    if orden.estado == Orden.Estado.RECIBIDA:
        return usuario.rol == User.Rol.RECEPCIONISTA
    return usuario.rol == User.Rol.OPERARIO and orden.operario_id == usuario.pk


class CambiarEstadoView(APIView):
    def post(self, request, pk):
        entrada = CambioEstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        nuevo = entrada.validated_data["estado"]
        with operacion_sobre_orden():
            orden = get_object_or_404(Orden.objects.select_for_update(), pk=pk)
            if not puede_cambiar_estado(request.user, orden):
                raise PermissionDenied("No tienes permiso para cambiar el estado de esta orden.")
            anterior = orden.estado
            orden.cambiar_estado(nuevo)
            orden.registrar_autoria(request.user)
            orden.save()
            detalle = f"{anterior} → {nuevo}"
            if nuevo == Orden.Estado.EN_PROCESO and anterior == Orden.Estado.CONTROL_CALIDAD:
                detalle += f" (reproceso {orden.numero_reprocesos})"
            registrar_evento(orden, Evento.CAMBIO_ESTADO, request.user, detalle)
        return Response(OrdenSerializer(ordenes_con_detalle().get(pk=orden.pk)).data)


class AsignarOperarioView(APIView):
    permission_classes = [AdministradorORecepcionista]

    def post(self, request, pk):
        with operacion_sobre_orden():
            orden = get_object_or_404(Orden.objects.select_for_update(), pk=pk)
            # Se valida con la orden bloqueada para leer el estado del operario
            # dentro de la misma transaccion que la asignacion.
            entrada = AsignacionSerializer(data=request.data)
            entrada.is_valid(raise_exception=True)
            tipo, detalle = asignar_operario(
                orden, entrada.validated_data["operario"], request.user
            )
            registrar_evento(orden, tipo, request.user, detalle)
        return Response(OrdenSerializer(ordenes_con_detalle().get(pk=orden.pk)).data)


class OperariosActivosView(generics.ListAPIView):
    serializer_class = OperarioSerializer
    permission_classes = [AdministradorORecepcionista]

    def get_queryset(self):
        return operarios_activos().order_by("first_name", "last_name", "username")


class HistorialOrdenView(generics.ListAPIView):
    """Solo lectura: el historial no expone escritura por ningun metodo."""

    serializer_class = HistorialOrdenSerializer
    permission_classes = [AdministradorORecepcionista]

    def get_queryset(self):
        orden = get_object_or_404(Orden, pk=self.kwargs["pk"])
        return orden.historial.select_related("usuario")
