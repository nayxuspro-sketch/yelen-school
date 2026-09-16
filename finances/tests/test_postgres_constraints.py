"""Scénarios d'intégrité exécutés uniquement avec PostgreSQL.

Les gardes ``Model.save()`` protègent le chemin Django, mais une mise à jour
``QuerySet.update()`` ou SQL direct ne déclenche pas ``save()``. Ces scénarios
valident donc les contraintes CHECK réellement installées par migration.
"""

from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction
from model_bakery import baker

from finances.models import (
    BourseEleve,
    BudgetAnnuel,
    DemandePaiementMobile,
    Depense,
    Echeancier,
    FraisScolarite,
    HistoriqueRelance,
    Paiement,
    Remboursement,
)


pytestmark = pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='La validation de production exige PostgreSQL ; SQLite est interdit.',
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('model', 'field', 'invalid_value'),
    (
        (FraisScolarite, 'montant', Decimal('0')),
        (Paiement, 'montant', Decimal('0')),
        (Remboursement, 'montant', Decimal('0')),
        (Echeancier, 'montant_du', Decimal('0')),
        (BourseEleve, 'montant_accorde', Decimal('0')),
        (HistoriqueRelance, 'montant_reclame', Decimal('0')),
        (DemandePaiementMobile, 'montant', Decimal('0')),
        (BudgetAnnuel, 'montant_prevu', Decimal('-1')),
        (Depense, 'montant', Decimal('0')),
    ),
)
def test_postgres_rejects_direct_invalid_financial_update(model, field, invalid_value):
    kwargs = {field: Decimal('100')}
    if model is BourseEleve:
        kwargs['type_bourse'] = baker.make(
            'finances.TypeBourse',
            type_reduction='MONTANT_FIXE',
            valeur_reduction=Decimal('100'),
        )
    instance = baker.make(model, **kwargs)

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            model.objects.filter(pk=instance.pk).update(**{field: invalid_value})

    assert model.objects.filter(pk=instance.pk).values_list(field, flat=True).get() == Decimal('100')


@pytest.mark.django_db(transaction=True)
def test_postgres_constraints_are_installed_for_all_financial_models():
    expected = {
        'frais_montant_positif',
        'paiement_montant_positif',
        'remboursement_montant_positif',
        'echeancier_montant_positif',
        'bourse_montant_positif',
        'relance_montant_positif',
        'mobile_money_montant_positif',
        'budget_montant_non_negatif',
        'depense_montant_positif',
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE connamespace = current_schema()::regnamespace
              AND conname = ANY(%s)
            """,
            [list(expected)],
        )
        installed = {row[0] for row in cursor.fetchall()}

    assert installed == expected
