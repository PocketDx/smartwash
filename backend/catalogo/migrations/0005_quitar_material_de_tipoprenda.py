from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0004_unificar_tipos_por_material'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tipoprenda',
            name='material',
        ),
    ]
