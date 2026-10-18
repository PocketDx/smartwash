"""Contrato compartido para registrar el historial de una orden.

Toda historia que cambie una orden hace el cambio y su registro juntos:

    with operacion_sobre_orden():
        orden.estado = Orden.Estado.CLASIFICADA
        orden.registrar_autoria(request.user)
        orden.save()
        registrar_evento(
            orden, HistorialOrden.TipoEvento.CAMBIO_ESTADO, request.user,
            "Recibida → Clasificada",
        )

Si algo falla en la base, no queda ni el cambio ni el registro.
"""

import logging
from contextlib import contextmanager

from django.core.exceptions import ValidationError as ReglaIncumplida
from django.db import DatabaseError, transaction
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from .models import HistorialOrden

logger = logging.getLogger(__name__)


class OperacionNoCompletada(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "No se pudo completar la operación. No se aplicó ningún cambio."
    default_code = "operacion_no_completada"


@contextmanager
def operacion_sobre_orden():
    # El detalle del error de base va al log, nunca a la respuesta.
    try:
        with transaction.atomic():
            yield
    except ReglaIncumplida as error:
        # Las reglas viven en el modelo con la excepcion de Django; la API
        # las devuelve como un 400 con el mismo mensaje.
        detalle = error.message_dict if hasattr(error, "error_dict") else error.messages
        raise serializers.ValidationError(detalle) from error
    except DatabaseError as error:
        logger.exception("Operacion sobre una orden revertida por un error de base de datos")
        raise OperacionNoCompletada from error


def registrar_evento(orden, tipo_evento, usuario, detalle=""):
    if tipo_evento not in HistorialOrden.TipoEvento.values:
        raise ValueError(f"Tipo de evento desconocido: {tipo_evento!r}")
    # Fuera de una transaccion, el cambio podria quedar guardado sin su registro.
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError(
            "registrar_evento debe llamarse dentro de la transaccion del cambio "
            "(usa operacion_sobre_orden)."
        )
    if usuario is not None and not usuario.is_authenticated:
        usuario = None
    return HistorialOrden.objects.create(
        orden=orden, tipo_evento=tipo_evento, usuario=usuario, detalle=detalle
    )
