import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('catalogo', '0007_niveles_iniciales')]

    operations = [
        migrations.AlterField(
            model_name='material',
            name='nivel_dificultad',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='materiales', to='catalogo.niveldificultad'),
        ),
    ]
