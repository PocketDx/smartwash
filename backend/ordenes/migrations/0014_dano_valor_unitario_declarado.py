from decimal import Decimal

from django.db import migrations, models


def valor_por_unidad(apps, schema_editor):
    # El total (valor_declarado) no se toca: solo se reparte entre las unidades afectadas.
    DanoPrenda = apps.get_model("ordenes", "DanoPrenda")
    for dano in DanoPrenda.objects.all():
        dano.valor_unitario_declarado = (dano.valor_declarado / dano.cantidad_afectada).quantize(
            Decimal("0.01")
        )
        dano.save(update_fields=["valor_unitario_declarado"])


class Migration(migrations.Migration):

    dependencies = [
        ("ordenes", "0013_dano_cantidad_afectada"),
    ]

    operations = [
        migrations.AddField(
            model_name="danoprenda",
            name="valor_unitario_declarado",
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.RunPython(valor_por_unidad, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="danoprenda",
            name="valor_unitario_declarado",
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AddConstraint(
            model_name="danoprenda",
            constraint=models.CheckConstraint(
                condition=models.Q(("valor_unitario_declarado__gt", 0)),
                name="dano_valor_unitario_declarado_positivo",
            ),
        ),
    ]
