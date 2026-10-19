from decimal import Decimal

from django.db import migrations

NIVELES = (("Fácil", Decimal("1.00")), ("Medio", Decimal("1.30")), ("Difícil", Decimal("1.60")))


def crear_niveles_y_asignar(apps, schema_editor):
    """Siembra los tres niveles y deja los materiales existentes en "Fácil"
    (factor 1.00), de modo que ningun precio cambie."""
    Nivel = apps.get_model("catalogo", "NivelDificultad")
    Material = apps.get_model("catalogo", "Material")
    niveles = {n: Nivel.objects.get_or_create(nombre=n, defaults={"factor": f})[0] for n, f in NIVELES}
    Material.objects.filter(nivel_dificultad__isnull=True).update(nivel_dificultad=niveles["Fácil"])


class Migration(migrations.Migration):
    """Al deshacerla no se borran los niveles sembrados ni se desasignan los
    materiales: al volver a aplicarla se reutilizan (get_or_create)."""

    dependencies = [("catalogo", "0006_niveldificultad")]

    operations = [migrations.RunPython(crear_niveles_y_asignar, migrations.RunPython.noop)]
