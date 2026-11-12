# Fecha estimada de entrega

**Proyecto:** SmartWash
**Historias relacionadas:** HU09 (registro de la orden), HU16 (alertas de vencimiento), HU17 (consulta pública del estado)
**Código:** `backend/ordenes/estimacion.py`

> **Regla interna.** Las duraciones, el margen y los rangos de prendas son constantes del sistema. No se editan desde la interfaz ni salen en ninguna API, ni para el cliente ni para el administrador o la recepcionista. Lo único que se expone es la fecha final.

## Por qué cambió

Antes, la fecha se fijaba al alcanzar el abono y no se volvía a tocar. Una orden recibida el 18 de octubre mostraba "entrega el 20 de octubre" aunque el 11 de noviembre siguiera en "Clasificada". Ahora la fecha sale de **por dónde va el flujo** y se recalcula cuando la orden avanza o se atrasa.

## Duración de cada etapa

| Etapa | Duración |
|---|---|
| Recibida | 0 h |
| Clasificada | 12 h |
| En proceso | Según el total de prendas (ver tabla) |
| Control de calidad | 12 h |
| Lista para entrega, pago y entrega | No cuentan: dependen del cliente |

**En proceso, por total de prendas** (suma de las cantidades de las líneas, sin las unidades ya dañadas o perdidas). El límite superior de cada rango es inclusivo:

| Prendas | Horas |
|---|---|
| 1 a 4 | 24 |
| 5 a 7 | 48 |
| 8 a 10 | 72 |
| 11 a 15 | 96 |
| 16 a 20 | 120 |
| 21 a 30 | 144 |
| 31 a 40 | 168 |
| 41 a 50 | 192 |
| … | +24 por cada 10 prendas más |

## Cálculo

1. Se toma la **etapa actual** y el momento en que la orden **entró** a ella, según el historial de la orden (el último cambio de estado hacia esa etapa).
2. Horas = las de la etapa actual + las de las etapas siguientes. Las horas se suman primero y solo al final se pasan a días.
3. Días = horas ÷ 24, **redondeado siempre hacia arriba**. Por ejemplo, 48 h son 2 días y 60 h son 3 días.
4. Esos días se cuentan como **días hábiles** desde el día en que la orden entró a la etapa.

Ejemplo: una orden de 3 prendas recién recibida: 0 + 12 + 24 + 12 = 48 h = 2 días hábiles.

### Casos especiales

- **Recibida.** No tiene duración propia, así que no puede atrasarse. Mientras la orden no se clasifique, lo que falta se cuenta desde el momento actual.
- **Etapa atrasada.** Si ya pasó la duración de la etapa actual, la fecha se recalcula **desde ahora**: 12 h de margen para la etapa atrasada más las etapas siguientes, con el mismo redondeo y los mismos días hábiles.
- **Reproceso.** Si la orden vuelve a "En proceso" (control de calidad que no aprueba, novedad con "agregar servicio" o "reprocesar con descuento"), el tiempo de En proceso se cuenta de nuevo desde ese reingreso.
- **Con novedad.** Se estima desde la etapa en la que estaba la orden cuando se detuvo.
- **Lista para entrega y Entregada.** Se conserva la última estimación; no se recalcula hacia el pasado.
- **En espera y Cancelada.** No tienen fecha estimada.
- **Nunca en el pasado.** Si el cálculo diera una fecha anterior a hoy, se usa hoy, o el siguiente día hábil si hoy no lo es.

## Días hábiles

La lavandería trabaja de **lunes a sábado**. No cuentan los domingos ni los **festivos de Colombia**: se usa la librería `holidays` (`holidays.country_holidays("CO")`), que incluye los festivos trasladados al lunes y Semana Santa, así que no hay fechas escritas a mano.

- Se avanza día a día y solo cuentan los días hábiles. Una orden de 2 días recibida un **sábado** se entrega el **martes**; si ese lunes es festivo, el **miércoles**.
- Con 0 días, o si la fecha de referencia cae en domingo o festivo, el resultado es la misma fecha si es hábil, o el siguiente día hábil.
- La fecha final nunca es domingo ni festivo.

## Dónde se usa

- **Se calcula al leer.** El detalle y el listado de órdenes, la bandeja del operario y la consulta pública de rastreo exponen la fecha calculada en el momento de la consulta, así que se actualiza sola con el paso del tiempo.
- **Caché para las alertas (HU16).** El campo `Orden.fecha_estimada_entrega` guarda la estimación vigente y se actualiza en cada cambio de la orden, porque cada evento del historial la recalcula. Las alertas de vencimiento comparan ese campo con hoy: si la orden se queda quieta, la fecha guardada pasa y la orden sale como "retrasada". La fecha calculada al leer, en cambio, nunca queda en el pasado.
- **Órdenes existentes.** Se recalculan solas al leerlas; no hace falta migración de datos. El campo `duracion_estimada_dias` de la regla anterior se eliminó (migración `0015`).
