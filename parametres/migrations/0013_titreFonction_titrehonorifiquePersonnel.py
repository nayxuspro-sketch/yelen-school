import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0012_add_cycle_to_typedocument'),
    ]

    operations = [
        migrations.CreateModel(
            name='TitreFonction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nom', models.CharField(help_text='Ex: Directeur, Censeur, Professeur Principal', max_length=100, unique=True, verbose_name='Titre / Fonction')),
                ('actif', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'verbose_name': 'Titre Fonction',
                'verbose_name_plural': 'Titres Fonctions',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='TitreHonorifiquePersonnel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nom', models.CharField(help_text="Ex: M. le Directeur, Chevalier de l'Ordre des Palmes académiques", max_length=150, unique=True, verbose_name='Titre honorifique')),
                ('actif', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'verbose_name': 'Titre Honorifique',
                'verbose_name_plural': 'Titres Honorifiques',
                'ordering': ['nom'],
            },
        ),
    ]
