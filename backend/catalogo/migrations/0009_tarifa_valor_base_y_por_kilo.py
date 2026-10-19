from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('catalogo', '0008_material_nivel_obligatorio')]

    operations = [
        migrations.AddField(
            model_name='tarifa',
            name='valor_base',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Se cobra por cada prenda, pese lo que pese.', max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tarifa',
            name='precio_por_kilo',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Se multiplica por el peso de la prenda en kg.', max_digits=10),
            preserve_default=False,
        ),
        # El default permite volver a crear la columna al deshacer 0011.
        migrations.AlterField(
            model_name='tarifa',
            name='valor',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
