from django.db import migrations

# La clave de agrupacion ignora mayusculas y espacios sobrantes: "Camisa" y
# "camisa " son el mismo tipo. Ademas, si el nombre termina en "(<material>)" y
# ese texto es el material del propio tipo, el parentesis se descarta
# ("Camisa (Algodon)" con material "Algodon" pasa a "Camisa"). Cualquier otra
# forma de repetir un tipo ("Camisa de jean") no se puede deducir y queda como
# esta; el administrador la fusiona a mano.


def limpiar(texto):
    return " ".join((texto or "").split())


def base_del_nombre(nombre, material):
    nombre, material = limpiar(nombre), limpiar(material)
    if material:
        sufijo = f"({material})".casefold()
        if nombre.casefold().endswith(sufijo):
            base = nombre[: -len(sufijo)].rstrip()
            if base:
                return base
    return nombre


def mismas_condiciones(a, b):
    return (a.valor, a.unidad_cobro, a.plazo_entrega_dias) == (
        b.valor,
        b.unidad_cobro,
        b.plazo_entrega_dias,
    )


def agrupar_tipos(TipoPrenda):
    grupos = {}
    for tipo in TipoPrenda.objects.order_by("id"):
        base = base_del_nombre(tipo.nombre, tipo.material)
        grupos.setdefault(base.casefold(), []).append((tipo, base))
    return grupos


def buscar_conflictos(grupos, Tarifa):
    """Dos tarifas vigentes del mismo servicio que quedarian bajo un solo tipo
    con condiciones distintas: no hay forma de elegir una sin perder la otra."""
    conflictos = []
    for miembros in grupos.values():
        if len(miembros) < 2:
            continue
        por_servicio = {}
        for tipo, _ in miembros:
            for tarifa in Tarifa.objects.filter(tipo_prenda=tipo, vigente_hasta__isnull=True):
                por_servicio.setdefault(tarifa.servicio_id, []).append((tipo, tarifa))
        for servicio_id, tarifas in por_servicio.items():
            if any(not mismas_condiciones(tarifas[0][1], t) for _, t in tarifas[1:]):
                detalle = "; ".join(
                    f'"{tipo.nombre}" ({tipo.material or "sin material"}) = {t.valor} por '
                    f"{t.unidad_cobro}, {t.plazo_entrega_dias} dias"
                    for tipo, t in tarifas
                )
                conflictos.append(f"servicio {servicio_id}: {detalle}")
    return conflictos


def unificar(apps, schema_editor):
    TipoPrenda = apps.get_model("catalogo", "TipoPrenda")
    Material = apps.get_model("catalogo", "Material")
    Tarifa = apps.get_model("catalogo", "Tarifa")
    Prenda = apps.get_model("ordenes", "Prenda")
    OrdenServicio = apps.get_model("ordenes", "OrdenServicio")

    grupos = agrupar_tipos(TipoPrenda)
    conflictos = buscar_conflictos(grupos, Tarifa)
    if conflictos:
        raise RuntimeError(
            "No se puede unificar los tipos de prenda: hay tarifas vigentes del mismo "
            "servicio con valor, unidad o plazo distintos. Deja una sola tarifa vigente "
            "por servicio entre los tipos que se van a unir (cierra la sobrante) y vuelve "
            "a migrar.\n  " + "\n  ".join(conflictos)
        )

    materiales = {}

    def material_de(texto):
        texto = limpiar(texto)
        if not texto:
            return None
        if texto.casefold() not in materiales:
            existente = Material.objects.filter(nombre__iexact=texto).first()
            materiales[texto.casefold()] = existente or Material.objects.create(nombre=texto)
        return materiales[texto.casefold()]

    for miembros in grupos.values():
        canonico, base = miembros[0]
        for tipo, _ in miembros:
            material = material_de(tipo.material)
            if material is not None:
                Prenda.objects.filter(tipo_prenda=tipo).update(material=material)
        for duplicado, _ in miembros[1:]:
            Prenda.objects.filter(tipo_prenda=duplicado).update(tipo_prenda=canonico)
            for tarifa in Tarifa.objects.filter(tipo_prenda=duplicado).order_by("id"):
                vigente = (
                    Tarifa.objects.filter(
                        tipo_prenda=canonico,
                        servicio_id=tarifa.servicio_id,
                        vigente_hasta__isnull=True,
                    ).first()
                    if tarifa.vigente_hasta is None
                    else None
                )
                if vigente is None:
                    Tarifa.objects.filter(pk=tarifa.pk).update(tipo_prenda=canonico)
                    continue
                # Misma tarifa vigente repetida (ya se comprobo que coincide):
                # las ordenes ya cobradas pasan a la que se conserva y esta
                # arranca en la fecha mas antigua de las dos.
                OrdenServicio.objects.filter(tarifa=tarifa).update(tarifa=vigente)
                if tarifa.vigente_desde < vigente.vigente_desde:
                    Tarifa.objects.filter(pk=vigente.pk).update(vigente_desde=tarifa.vigente_desde)
                tarifa.delete()
            duplicado.delete()
        if canonico.nombre != base:
            TipoPrenda.objects.filter(pk=canonico.pk).update(nombre=base)


class Migration(migrations.Migration):
    """Pasa el texto TipoPrenda.material a la tabla Material y une los tipos repetidos.

    Reversible solo en el esquema: al deshacerla no se vuelven a separar los
    tipos unidos ni se rellena TipoPrenda.material (ya no hay de donde saber
    que tipo era cada uno). La orden de las prendas conserva su material.
    """

    dependencies = [
        ("catalogo", "0003_material"),
        ("ordenes", "0004_prenda_material"),
    ]

    operations = [
        migrations.RunPython(unificar, migrations.RunPython.noop),
    ]
