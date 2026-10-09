"""Scénarios PostgreSQL des parcours financiers sensibles.

Ces tests doivent être exécutés avec la base PostgreSQL officielle. Ils
couvrent les contrôles qui ne peuvent pas être prouvés par des objets Django
non persistés : IDOR entre établissements, verrous concurrents, plafonds de
remboursement et confirmation Mobile Money idempotente.
"""

from decimal import Decimal
from threading import Barrier, Thread

import pytest
from django.db import IntegrityError, close_old_connections, connection, models, transaction
from django.urls import reverse
from model_bakery import baker

from core.models import AuditLog
from finances.models import (
    DemandePaiementMobile,
    ModePaiement,
    Paiement,
    Remboursement,
)


pytestmark = pytest.mark.django_db(transaction=True)

# Triggers, verrous de lignes et accès concurrents : garanties du moteur PostgreSQL.
# En mode autonome SQLite ces scénarios ne s'appliquent pas (base mono-fichier,
# écrivain unique) ; les contrôles applicatifs (IDOR, rôles, soft delete) restent testés.
postgresql_uniquement = pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='Garanties spécifiques PostgreSQL (triggers / verrous)',
)


@pytest.fixture
def audit_actif():
    """Réactive le journal d'audit, désactivé globalement par conftest.py."""
    from core.signals import disable_audit, enable_audit
    enable_audit()
    yield
    disable_audit()


@pytest.fixture
def financial_school():
    etablissement = baker.make('etablissements.Etablissement')
    cycle = baker.make('parametres.Cycle', etablissement=etablissement)
    classe = baker.make(
        'parametres.Classe',
        etablissement=etablissement,
        cycle=cycle,
        niveau='6EME',
    )
    annee = baker.make(
        'parametres.AnneeScolaire',
        etablissement=etablissement,
        est_courante=True,
    )
    statut = baker.make('parametres.StatutEleve', etablissement=etablissement)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etablissement)
    tarif = baker.make(
        'parametres.TarifScolarite',
        etablissement=etablissement,
        classe=classe,
        annee_scolaire=annee,
        statut_eleve=statut,
        rubrique=rubrique,
        montant=100,
        actif=True,
    )
    inscription = baker.make(
        'inscriptions.Inscription',
        classe=classe,
        annee_scolaire=annee,
        statut_eleve=statut,
    )
    users = [
        baker.make(
            'accounts.User',
            role='COMPTABLE',
            etablissement=etablissement,
            totp_enabled=True,
            must_change_password=False,
            is_active=True,
        )
        for _ in range(2)
    ]
    approvers = [
        baker.make(
            'accounts.User',
            role='DIRECTEUR',
            etablissement=etablissement,
            totp_enabled=True,
            must_change_password=False,
            is_active=True,
        )
        for _ in range(2)
    ]
    return {
        'etablissement': etablissement,
        'annee': annee,
        'rubrique': rubrique,
        'tarif': tarif,
        'inscription': inscription,
        'users': users,
        'approvers': approvers,
    }


def _concurrent_posts(url, users, data):
    """Exécute un POST par connexion Django indépendante et retourne les réponses."""
    barrier = Barrier(len(users))
    responses = {}
    failures = []

    def worker(index, user):
        from django.test import Client

        close_old_connections()
        try:
            client = Client()
            client.force_login(user)
            barrier.wait(timeout=15)
            responses[index] = client.post(url, data=data)
        except BaseException as exc:  # remonter l'erreur dans le thread principal
            failures.append(exc)
        finally:
            close_old_connections()

    threads = [Thread(target=worker, args=(index, user)) for index, user in enumerate(users)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    if failures:
        raise failures[0]
    assert len(responses) == len(users), 'Un worker concurrent ne s’est pas terminé.'
    return responses


def test_financial_idor_is_rejected_for_api_and_mobile_money(financial_school, client):
    other_school_user = baker.make(
        'accounts.User',
        role='COMPTABLE',
        totp_enabled=True,
        must_change_password=False,
        is_active=True,
    )
    other_school = baker.make('etablissements.Etablissement')
    other_school_user.etablissement = other_school
    other_school_user.save(update_fields=['etablissement'])

    client.force_login(other_school_user)
    inscription_url = reverse(
        'finances:api_rubriques',
        kwargs={'inscription_id': financial_school['inscription'].pk},
    )
    response = client.get(inscription_url)
    assert response.status_code == 403

    demande = DemandePaiementMobile.objects.create(
        inscription=financial_school['inscription'],
        montant=50,
        telephone='70123456',
        rubrique=financial_school['rubrique'],
    )
    confirm_url = reverse('finances:mobile_money_confirmer', kwargs={'pk': demande.pk})
    response = client.post(confirm_url, {'reference_transaction': 'OUTSIDER'})
    assert response.status_code == 403
    demande.refresh_from_db()
    assert demande.paiement_id is None
    assert Paiement.objects.filter(inscription=financial_school['inscription']).count() == 0


def test_cross_school_situation_is_rejected(financial_school, client):
    other_school = baker.make('etablissements.Etablissement')
    user = baker.make(
        'accounts.User',
        role='DIRECTEUR',
        etablissement=other_school,
        totp_enabled=True,
        must_change_password=False,
        is_active=True,
    )
    client.force_login(user)

    response = client.get(
        reverse(
            'finances:situation_eleve',
            kwargs={'inscription_id': financial_school['inscription'].pk},
        )
    )
    assert response.status_code == 403


def test_refund_cancellation_is_soft_deleted_and_audited(financial_school, client, audit_actif):
    user = financial_school['approvers'][0]
    client.force_login(user)
    paiement = Paiement.objects.create(
        inscription=financial_school['inscription'],
        rubrique=financial_school['rubrique'],
        montant=100,
        mode_paiement=ModePaiement.ESPECES,
        encaisse_par=user,
    )
    remboursement = Remboursement.objects.create(
        paiement=paiement,
        montant=40,
        motif='Erreur de caisse',
        rembourse_par=user,
    )

    response = client.post(
        reverse(
            'finances:remboursement_delete',
            kwargs={'remboursement_id': remboursement.pk},
        ),
        {'motif': 'Annulation contrôlée du remboursement'},
    )
    assert response.status_code == 302
    remboursement.refresh_from_db()
    assert remboursement.is_active is False
    audit = AuditLog.objects.filter(
        model_name='remboursement',
        object_id=str(remboursement.pk),
        action='UPDATE',
    ).order_by('-timestamp').first()
    assert audit is not None
    assert audit.reason == 'Annulation contrôlée du remboursement'


@postgresql_uniquement
def test_database_blocks_direct_payment_mutation_and_refund_overflow(financial_school):
    paiement = Paiement.objects.create(
        inscription=financial_school['inscription'],
        rubrique=financial_school['rubrique'],
        montant=100,
        mode_paiement=ModePaiement.ESPECES,
        encaisse_par=financial_school['users'][0],
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Paiement.objects.filter(pk=paiement.pk).update(montant=Decimal('90'))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Paiement.objects.filter(pk=paiement.pk).delete()

    remboursement = Remboursement.objects.create(
        paiement=paiement,
        montant=80,
        motif='Remboursement initial',
        rembourse_par=financial_school['approvers'][0],
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Remboursement.objects.filter(pk=remboursement.pk).update(is_active=False)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # bulk_create contourne save() : le trigger doit tout de même
            # empêcher un remboursement qui dépasse le paiement d'origine.
            Remboursement.objects.bulk_create([
                Remboursement(
                    paiement=paiement,
                    montant=Decimal('30'),
                    motif='Dépassement direct',
                    rembourse_par=financial_school['approvers'][1],
                )
            ])


@postgresql_uniquement
def test_concurrent_payments_cannot_exceed_the_tariff(financial_school):
    inscription = financial_school['inscription']
    url = reverse('finances:paiement_create')
    data = {
        'inscription': str(inscription.pk),
        'mode_paiement': ModePaiement.ESPECES,
        'rubrique_ids[]': [str(financial_school['rubrique'].pk)],
        'montants[]': ['60'],
        'echeances[]': [''],
    }
    responses = _concurrent_posts(url, financial_school['users'], data)

    assert sorted(response.status_code for response in responses.values()) == [200, 302]
    paiements = Paiement.objects.filter(inscription=inscription)
    assert paiements.count() == 1
    assert paiements.aggregate(total=models.Sum('montant'))['total'] == Decimal('60')


@postgresql_uniquement
def test_concurrent_refunds_are_capped_by_the_original_payment(financial_school):
    paiement = Paiement.objects.create(
        inscription=financial_school['inscription'],
        rubrique=financial_school['rubrique'],
        montant=100,
        mode_paiement=ModePaiement.ESPECES,
        encaisse_par=financial_school['approvers'][0],
    )
    url = reverse('finances:remboursement_create', kwargs={'paiement_id': paiement.pk})
    data = {
        'montant': '75',
        'motif': 'Remboursement concurrent de test',
        'date_remboursement': '2026-09-16',
    }
    responses = _concurrent_posts(url, financial_school['approvers'], data)

    assert sorted(response.status_code for response in responses.values()) == [200, 302]
    assert Remboursement.objects.filter(paiement=paiement, is_active=True).count() == 1
    assert Remboursement.objects.filter(paiement=paiement, is_active=True).aggregate(
        total=models.Sum('montant')
    )['total'] == Decimal('75')


@postgresql_uniquement
def test_concurrent_mobile_money_confirmation_is_idempotent(financial_school):
    demande = DemandePaiementMobile.objects.create(
        inscription=financial_school['inscription'],
        montant=100,
        telephone='70123456',
        rubrique=financial_school['rubrique'],
    )
    url = reverse('finances:mobile_money_confirmer', kwargs={'pk': demande.pk})
    responses = _concurrent_posts(
        url,
        financial_school['users'],
        {'reference_transaction': 'MM-CONCURRENT'},
    )

    assert all(response.status_code == 302 for response in responses.values())
    demande.refresh_from_db()
    assert demande.statut == DemandePaiementMobile.StatutChoices.CONFIRME
    assert demande.paiement_id is not None
    assert Paiement.objects.filter(inscription=financial_school['inscription']).count() == 1
