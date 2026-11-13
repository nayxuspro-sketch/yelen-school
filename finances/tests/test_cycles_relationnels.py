"""Préservation des données pendant la conversion des cycles vers parametres.Cycle."""
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


AVANT = [
    ('etablissements', '0005_cycles_arrayfield_to_jsonfield'),
    ('parametres', '0048_nettoyage_cosignataire_doublons'),
    ('finances', '0023_lot_f_caisse_parametres'),
    ('manuels', '0003_prets_echeance_retour'),
]
APRES = [
    ('etablissements', '0006_cycles_relationnels'),
    ('parametres', '0049_directions_cycles_and_identity_labels'),
    ('finances', '0024_frais_scolarite_cycle_relationnel'),
    ('manuels', '0004_cycle_relationnel'),
]


@pytest.mark.django_db(transaction=True)
def test_cycles_relationnels_preservent_catalogue_et_frais_et_sont_reversibles():
    """Les codes historiques deviennent des FK sans perdre les cycles existants ni les données associées."""
    executor = MigrationExecutor(connection)
    executor.migrate(AVANT)
    apps = executor.loader.project_state(AVANT).apps

    Etablissement = apps.get_model('etablissements', 'Etablissement')
    AnneeScolaire = apps.get_model('parametres', 'AnneeScolaire')
    Cycle = apps.get_model('parametres', 'Cycle')
    FraisScolarite = apps.get_model('finances', 'FraisScolarite')
    ManuelScolaire = apps.get_model('manuels', 'ManuelScolaire')

    try:
        etab = Etablissement.objects.create(
            nom='École migration', code='MIG-CYCLES', ville='Sabou', cycles=['PRIMAIRE'],
        )
        cycle = Cycle.objects.create(
            etablissement=etab, code='PRIM', nom='Primaire personnalisé', ordre=7,
        )
        annee = AnneeScolaire.objects.create(
            etablissement=etab, libelle='2026-2027',
            date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30),
        )
        manuel = ManuelScolaire.objects.create(
            etablissement=etab, titre='Manuel conservé', cycle='PRIMAIRE',
        )
        frais = FraisScolarite.objects.create(
            annee_scolaire=annee, cycle='PRIMAIRE', montant=Decimal('50000'),
        )

        executor = MigrationExecutor(connection)
        executor.migrate(APRES)
        apps = executor.loader.project_state(APRES).apps
        Etablissement = apps.get_model('etablissements', 'Etablissement')
        Cycle = apps.get_model('parametres', 'Cycle')
        FraisScolarite = apps.get_model('finances', 'FraisScolarite')
        ManuelScolaire = apps.get_model('manuels', 'ManuelScolaire')

        manuel_relationnel = ManuelScolaire.objects.get(pk=manuel.pk)
        frais_relationnel = FraisScolarite.objects.get(pk=frais.pk)
        assert manuel_relationnel.cycle_id == cycle.pk
        assert manuel_relationnel.cycle.nom == 'Primaire personnalisé'
        assert manuel_relationnel.titre == 'Manuel conservé'
        assert frais_relationnel.cycle_id == cycle.pk
        assert frais_relationnel.cycle.nom == 'Primaire personnalisé'
        assert frais_relationnel.montant == Decimal('50000.00')
        assert Cycle.objects.filter(etablissement_id=etab.pk, code='PRIM').count() == 1
        assert not hasattr(Etablissement, 'cycles')

        executor = MigrationExecutor(connection)
        executor.migrate(AVANT)
        apps = executor.loader.project_state(AVANT).apps
        Etablissement = apps.get_model('etablissements', 'Etablissement')
        FraisScolarite = apps.get_model('finances', 'FraisScolarite')
        ManuelScolaire = apps.get_model('manuels', 'ManuelScolaire')
        assert Etablissement.objects.get(pk=etab.pk).cycles == ['PRIMAIRE']
        assert ManuelScolaire.objects.get(pk=manuel.pk).cycle == 'PRIMAIRE'
        assert FraisScolarite.objects.get(pk=frais.pk).cycle == 'PRIMAIRE'
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
