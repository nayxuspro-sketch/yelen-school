from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personnel', '0002_increase_matricule_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='membrepersonnel',
            name='titre_honorifique',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Ex: M. le Directeur, Le Proviseur, Dr.',
                max_length=150,
                verbose_name='Titre honorifique',
            ),
        ),
        migrations.AlterField(
            model_name='membrepersonnel',
            name='fonction',
            field=models.CharField(max_length=100, verbose_name='Titre'),
        ),
    ]
