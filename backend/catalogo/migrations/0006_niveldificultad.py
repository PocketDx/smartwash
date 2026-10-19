import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0005_quitar_material_de_tipoprenda'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NivelDificultad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('nombre', models.CharField(max_length=80, unique=True)),
                ('factor', models.DecimalField(decimal_places=2, help_text='Multiplica el precio de los servicios de las prendas de sus materiales.', max_digits=5)),
                ('actualizado_por', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('creado_por', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'nivel de dificultad',
                'verbose_name_plural': 'niveles de dificultad',
                'ordering': ('factor', 'nombre'),
                'constraints': [models.CheckConstraint(condition=models.Q(('factor__gt', 0)), name='nivel_dificultad_factor_positivo')],
            },
        ),
        migrations.AddField(
            model_name='material',
            name='nivel_dificultad',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='materiales', to='catalogo.niveldificultad'),
        ),
        migrations.AddField(
            model_name='tipoprenda',
            name='peso_estandar',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Kilos de una prenda tipica; prellena el peso al registrar la orden.', max_digits=5, null=True),
        ),
    ]
