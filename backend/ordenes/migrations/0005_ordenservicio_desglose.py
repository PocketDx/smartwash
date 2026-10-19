from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('ordenes', '0004_prenda_material')]

    operations = [
        migrations.AlterField(
            model_name='prenda',
            name='peso',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Kilos de UNA prenda. La API lo exige; es nulo solo en prendas anteriores.', max_digits=7, null=True),
        ),
        migrations.AddField(model_name='ordenservicio', name='valor_base', field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='ordenservicio', name='precio_por_kilo', field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='ordenservicio', name='peso', field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
        migrations.AddField(model_name='ordenservicio', name='nivel_dificultad', field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name='ordenservicio', name='factor', field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
        migrations.AddField(model_name='ordenservicio', name='es_excepcion', field=models.BooleanField(blank=True, null=True)),
    ]
