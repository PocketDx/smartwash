from dataclasses import dataclass
from decimal import Decimal

from .models import Tarifa, redondear_a_100


@dataclass(frozen=True)
class PrecioCalculado:
    tarifa: Tarifa
    es_excepcion: bool
    peso: Decimal
    nivel: str
    factor: Decimal
    precio_unitario: Decimal


def calcular_precio(tarifa, peso, material):
    """Precio de UNA prenda para un servicio:
    redondear_a_100((valor_base + peso * precio_por_kilo) * factor del nivel del material).
    Sin material (prendas anteriores) el factor es 1."""
    nivel = material.nivel_dificultad if material is not None else None
    factor = nivel.factor if nivel is not None else Decimal("1")
    bruto = (tarifa.valor_base + peso * tarifa.precio_por_kilo) * factor
    return PrecioCalculado(
        tarifa=tarifa,
        es_excepcion=tarifa.tipo_prenda_id is not None,
        peso=peso,
        nivel=nivel.nombre if nivel is not None else "",
        factor=factor,
        precio_unitario=redondear_a_100(bruto),
    )
