import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0003_material'),
        ('ordenes', '0003_registro_orden'),
    ]

    operations = [
        migrations.AddField(
            model_name='prenda',
            name='material',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='prendas', to='catalogo.material'),
        ),
    ]
