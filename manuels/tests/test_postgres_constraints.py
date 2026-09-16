"""Scénarios d'intégrité du module manuels exécutés sur PostgreSQL réel."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from model_bakery import baker

from manuels.models import AttributionManuel, ManuelScolaire


pytestmark = pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='La validation de production exige PostgreSQL ; SQLite est interdit.',
)


@pytest.mark.django_db(transaction=True)
def test_postgres_rejects_negative_replacement_price():
    manuel = baker.make(ManuelScolaire, prix_remplacement=Decimal('100'))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ManuelScolaire.objects.filter(pk=manuel.pk).update(
                prix_remplacement=Decimal('-1'),
            )

    assert ManuelScolaire.objects.values_list(
        'prix_remplacement', flat=True,
    ).get(pk=manuel.pk) == Decimal('100')


@pytest.mark.django_db(transaction=True)
def test_postgres_rejects_two_active_attributions_for_one_copy():
    attribution = baker.make(
        AttributionManuel,
        date_retour=None,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AttributionManuel.objects.create(
                exemplaire=attribution.exemplaire,
                inscription=attribution.inscription,
                date_attribution=attribution.date_attribution,
                date_retour=None,
            )

    assert AttributionManuel.objects.filter(
        exemplaire=attribution.exemplaire,
        date_retour__isnull=True,
    ).count() == 1
