"""Migrations de données de la fiche élève."""
from datetime import date

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

AVANT = [('inscriptions', '0015_eleve_lieu_residence')]
APRES = [('inscriptions', '0016_eleve_supprimer_province_commune_village')]


@pytest.mark.django_db(transaction=True)
def test_0016_reporte_province_commune_village_dans_le_lieu_de_residence():
    """Les trois colonnes supprimées sont reportées dans « Lieu de résidence » quand il est vide ; sinon rien ne change."""
    executor = MigrationExecutor(connection)
    executor.migrate(AVANT)
    Eleve = executor.loader.project_state(AVANT).apps.get_model('inscriptions', 'Eleve')
    base = {'genre': 'M', 'date_naissance': date(2012, 1, 1), 'lieu_naissance': 'Bobo-Dioulasso'}
    Eleve.objects.create(matricule='M-1', nom='A', prenom='a', village='Dafra', commune='Bobo-Dioulasso',
                         province='Houet', **base)
    Eleve.objects.create(matricule='M-2', nom='B', prenom='b', commune='Ouagadougou', province=' Kadiogo ', **base)
    Eleve.objects.create(matricule='M-3', nom='C', prenom='c', lieu_residence='Secteur 15', village='Karpala', **base)
    Eleve.objects.create(matricule='M-4', nom='D', prenom='d', **base)

    executor = MigrationExecutor(connection)
    executor.migrate(APRES)
    Eleve = executor.loader.project_state(APRES).apps.get_model('inscriptions', 'Eleve')
    residences = dict(Eleve.objects.values_list('matricule', 'lieu_residence'))
    assert residences == {'M-1': 'Dafra, Bobo-Dioulasso, Houet', 'M-2': 'Ouagadougou, Kadiogo',
                          'M-3': 'Secteur 15', 'M-4': ''}
    assert not {'province', 'commune', 'village'} & {f.name for f in Eleve._meta.fields}
