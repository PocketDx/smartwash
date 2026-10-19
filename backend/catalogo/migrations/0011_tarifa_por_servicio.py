import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('catalogo', '0010_tarifas_actuales_como_excepciones')]

    operations = [
        migrations.RemoveConstraint(model_name='tarifa', name='tarifa_valor_no_negativo'),
        migrations.RemoveConstraint(model_name='tarifa', name='tarifa_vigente_unica_por_par'),
        migrations.RemoveField(model_name='tarifa', name='valor'),
        migrations.RemoveField(model_name='tarifa', name='unidad_cobro'),
        migrations.AlterField(
            model_name='tarifa',
            name='tipo_prenda',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tarifas', to='catalogo.tipoprenda'),
        ),
        migrations.AlterModelOptions(
            name='tarifa',
            options={'ordering': ('servicio__nombre', 'tipo_prenda__nombre', '-vigente_desde')},
        ),
        migrations.AddConstraint(
            model_name='tarifa',
            constraint=models.UniqueConstraint(condition=models.Q(('tipo_prenda__isnull', True), ('vigente_hasta__isnull', True)), fields=('servicio',), name='tarifa_general_vigente_unica'),
        ),
        migrations.AddConstraint(
            model_name='tarifa',
            constraint=models.UniqueConstraint(condition=models.Q(('tipo_prenda__isnull', False), ('vigente_hasta__isnull', True)), fields=('tipo_prenda', 'servicio'), name='tarifa_vigente_unica_por_par'),
        ),
        migrations.AddConstraint(
            model_name='tarifa',
            constraint=models.CheckConstraint(condition=models.Q(('valor_base__gte', 0), ('precio_por_kilo__gte', 0)), name='tarifa_valores_no_negativos'),
        ),
    ]
