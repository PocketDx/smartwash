from django.db import migrations
from django.db.models import F


def a_valor_base_y_por_kilo(apps, schema_editor):
    """Cada tarifa existente queda como excepcion por tipo de prenda: "por prenda"
    pasa a valor base y "por kilo" a precio por kilo. No se crea ninguna tarifa
    general; el administrador las carga despues."""
    Tarifa = apps.get_model("catalogo", "Tarifa")
    Tarifa.objects.filter(unidad_cobro="kilo").update(valor_base=0, precio_por_kilo=F("valor"))
    Tarifa.objects.filter(unidad_cobro="prenda").update(valor_base=F("valor"), precio_por_kilo=0)


def a_valor_y_unidad(apps, schema_editor):
    Tarifa = apps.get_model("catalogo", "Tarifa")
    for tarifa in Tarifa.objects.all():
        if tarifa.tipo_prenda_id is None:
            raise RuntimeError(
                "No se puede deshacer: hay tarifas generales por servicio, que el esquema "
                "anterior no sabe representar. Eliminalas o conviertelas en excepciones por tipo."
            )
        if tarifa.valor_base > 0 and tarifa.precio_por_kilo > 0:
            raise RuntimeError(
                f"No se puede deshacer: la tarifa {tarifa.pk} cobra valor base y precio por "
                "kilo a la vez, y el esquema anterior solo permite uno de los dos."
            )
        if tarifa.precio_por_kilo > 0:
            tarifa.valor, tarifa.unidad_cobro = tarifa.precio_por_kilo, "kilo"
        else:
            tarifa.valor, tarifa.unidad_cobro = tarifa.valor_base, "prenda"
        tarifa.save(update_fields=["valor", "unidad_cobro"])


class Migration(migrations.Migration):
    """Reversible solo mientras todas las tarifas sean excepciones por tipo que
    cobren valor base o precio por kilo, no ambos (ver a_valor_y_unidad)."""

    dependencies = [('catalogo', '0009_tarifa_valor_base_y_por_kilo')]

    operations = [migrations.RunPython(a_valor_base_y_por_kilo, a_valor_y_unidad)]
