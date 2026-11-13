"""Fecha estimada de entrega segun por donde va el flujo de la orden.

Regla interna (docs/fecha-estimada-de-entrega.md): las duraciones y el margen no se
editan desde la interfaz ni salen en ninguna API; solo se expone la fecha final.
"""

from datetime import timedelta
from math import ceil

import holidays
from django.utils import timezone

from .models import HistorialOrden, Orden

HORAS_CLASIFICACION = 12
HORAS_CONTROL_CALIDAD = 12
MARGEN_ETAPA_ATRASADA = 12
# (hasta cuantas prendas, horas en proceso). Por encima de 30, 24 h mas por cada 10 prendas.
HORAS_EN_PROCESO = ((4, 24), (7, 48), (10, 72), (15, 96), (20, 120), (30, 144))

ETAPAS_ESTIMADAS = (
    Orden.Estado.RECIBIDA,
    Orden.Estado.CLASIFICADA,
    Orden.Estado.EN_PROCESO,
    Orden.Estado.CONTROL_CALIDAD,
)
# Se trabaja de lunes a sabado; holidays cubre los festivos trasladados y Semana Santa.
FESTIVOS = holidays.country_holidays("CO")

Evento = HistorialOrden.TipoEvento
# Eventos cuyo detalle registra un cambio de estado "Estado A → Estado B".
EVENTOS_CON_TRANSICION = (
    Evento.CAMBIO_ESTADO,
    Evento.DECISION_NOVEDAD,
    Evento.NOVEDAD,
    Evento.ENTREGA,
    Evento.CANCELACION,
)


def estado_destino(detalle):
    """El estado al que entro la orden segun su detalle; None si no registra un cambio de estado.

    Se toma la ultima flecha con un estado a cada lado: el detalle puede traer otras, como la
    observacion de una decision o "Cliente: Ocasional → Frecuente" en la entrega.
    """
    partes = detalle.split(" → ")
    destino = None
    for antes, despues in zip(partes, partes[1:]):
        origen = next((e for e in Orden.Estado.values if antes.endswith(e)), None)
        llegada = next((e for e in Orden.Estado.values if despues.startswith(e)), None)
        if origen and llegada:
            destino = llegada
    return destino


def transiciones(orden):
    """(fecha, estado destino) de cada cambio de estado del historial, en orden cronologico."""
    return [
        (evento.fecha, destino)
        for evento in orden.historial.all()
        if evento.tipo_evento in EVENTOS_CON_TRANSICION and (destino := estado_destino(evento.detalle))
    ]


def es_dia_habil(dia):
    return dia.weekday() != 6 and dia not in FESTIVOS


def sumar_dias_habiles(fecha, dias):
    """Cuenta `dias` habiles despues de `fecha`; con 0, la misma fecha si es habil o la siguiente."""
    while dias == 0 and not es_dia_habil(fecha):
        fecha += timedelta(days=1)
    while dias > 0:
        fecha += timedelta(days=1)
        if es_dia_habil(fecha):
            dias -= 1
    return fecha


def horas_en_proceso(prendas):
    for tope, horas in HORAS_EN_PROCESO:
        if prendas <= tope:
            return horas
    return HORAS_EN_PROCESO[-1][1] + 24 * ceil((prendas - HORAS_EN_PROCESO[-1][0]) / 10)


def prendas_por_procesar(orden):
    """Unidades de la orden sin contar las ya danadas o perdidas, que no vuelven a proceso."""
    total = 0
    for prenda in orden.prendas.all():
        dano = getattr(prenda, "dano", None)
        total += prenda.cantidad - (dano.cantidad_afectada if dano else 0)
    return total


def horas_de(etapa, prendas):
    return {
        Orden.Estado.RECIBIDA: 0,
        Orden.Estado.CLASIFICADA: HORAS_CLASIFICACION,
        Orden.Estado.EN_PROCESO: horas_en_proceso(prendas),
        Orden.Estado.CONTROL_CALIDAD: HORAS_CONTROL_CALIDAD,
    }[etapa]


def etapa_estimada(orden):
    if orden.estado != Orden.Estado.CON_NOVEDAD:
        return orden.estado
    ultima = orden.novedades.order_by("creado_en", "id").last()
    return ultima.estado_anterior if ultima else Orden.Estado.EN_PROCESO


def calcular_fecha_estimada(orden, ahora=None, entrada=None):
    """Fecha estimada de entrega en hora de Bogota; None si todavia no aplica o ya no aplica.

    `entrada` es el momento en que la orden entro a su etapa actual cuando quien llama hace
    la transicion ahora y su evento aun no esta en el historial.
    """
    ahora = ahora or timezone.now()
    if orden.estado in (Orden.Estado.LISTA, Orden.Estado.ENTREGADA):
        # Lo que queda depende del cliente: se conserva la ultima estimacion.
        return orden.fecha_estimada_entrega
    etapa = etapa_estimada(orden)
    if etapa not in ETAPAS_ESTIMADAS:
        return None

    prendas = prendas_por_procesar(orden)
    indice = ETAPAS_ESTIMADAS.index(etapa)
    siguientes = sum(horas_de(e, prendas) for e in ETAPAS_ESTIMADAS[indice + 1 :])
    propias = horas_de(etapa, prendas)
    if entrada is None:
        entrada = next((f for f, destino in reversed(transiciones(orden)) if destino == etapa), None)
        entrada = entrada or orden.creado_en or ahora

    if propias == 0:
        # Recibida no tiene duracion propia: lo que falta corre desde ahora.
        desde, horas = max(entrada, ahora), siguientes
    elif ahora > entrada + timedelta(hours=propias):
        desde, horas = ahora, MARGEN_ETAPA_ATRASADA + siguientes
    else:
        desde, horas = entrada, propias + siguientes

    fecha = sumar_dias_habiles(timezone.localtime(desde).date(), ceil(horas / 24))
    return max(fecha, sumar_dias_habiles(timezone.localtime(ahora).date(), 0))


def actualizar_fecha_estimada(orden):
    """Guarda la estimacion vigente como cache; las alertas (HU16) la comparan con hoy."""
    if orden.pk is None or orden.estado not in ETAPAS_ESTIMADAS:
        return
    fresca = Orden.objects.prefetch_related("historial", "prendas__dano").get(pk=orden.pk)
    nueva = calcular_fecha_estimada(fresca)
    if nueva != fresca.fecha_estimada_entrega:
        Orden.objects.filter(pk=orden.pk).update(fecha_estimada_entrega=nueva)
    orden.fecha_estimada_entrega = nueva
