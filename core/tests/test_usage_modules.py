"""Compteur d'usage anonyme par module (P1-10, 5.48.0)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core import exploitation, signals, usage
from core.models import AuditLog, UsageModuleQuotidien

pytestmark = pytest.mark.django_db


def _connecter(client, role='SUPER_ADMIN'):
    etab = baker.make('etablissements.Etablissement')
    user = baker.make(
        'accounts.User',
        role=role,
        etablissement=etab,
        is_superuser=(role == 'SUPER_ADMIN'),
        must_change_password=False,
    )
    client.force_login(user)
    return user


def test_comptage_anonyme_par_module_et_exclusions(client):
    """Seules les vues métier servies à un utilisateur connecté sont comptées, sans donnée personnelle."""
    # Anonyme et /health/ : ignorés.
    assert client.get(reverse('core:health_check')).status_code == 200
    assert client.get(reverse('accounts:login')).status_code == 200
    assert usage.vider_tampon_usage() == 0

    _connecter(client, 'SUPER_ADMIN')
    assert client.get(reverse('core:home')).status_code == 200
    assert client.get(reverse('inscriptions:eleve_list')).status_code == 200
    assert client.get(reverse('inscriptions:eleve_list')).status_code == 200
    # Endpoints techniques de polling : ignorés.
    assert client.get(reverse('core:mise_a_jour_etat')).status_code == 200
    assert client.get(reverse('core:notifications_badge')).status_code == 200
    assert client.get('/page-introuvable-404/').status_code == 404

    bilan = usage.usage_modules()
    par_code = {m['module']: m for m in bilan['par_module']}
    assert par_code['inscriptions']['appels_7j'] == 2
    assert par_code['core']['appels_7j'] == 1
    assert bilan['total_7j'] == 3
    assert bilan['total_30j'] == 3


def test_fenetres_7j_30j_et_absence_d_audit():
    """Les compteurs distinguent 7 j / 30 j, ignorent au-delà de 30 j et ne polluent jamais AuditLog."""
    aujourd_hui = timezone.localdate()
    UsageModuleQuotidien.objects.create(date=aujourd_hui - timedelta(days=2), module='pedagogie', appels=15)
    UsageModuleQuotidien.objects.create(date=aujourd_hui - timedelta(days=15), module='pedagogie', appels=25)
    UsageModuleQuotidien.objects.create(date=aujourd_hui - timedelta(days=20), module='finances', appels=10)
    UsageModuleQuotidien.objects.create(date=aujourd_hui - timedelta(days=45), module='finances', appels=999)

    signals.enable_audit()
    try:
        avant_audit = AuditLog.objects.count()
        usage.enregistrer_appel_module('pedagogie', jour=aujourd_hui)
        usage.vider_tampon_usage()
        assert AuditLog.objects.count() == avant_audit
    finally:
        signals.disable_audit()

    bilan = usage.usage_modules()
    assert bilan['total_7j'] == 16
    assert bilan['total_30j'] == 51
    assert [m['module'] for m in bilan['par_module']] == ['pedagogie', 'finances']
    assert bilan['par_module'][0]['appels_7j'] == 16
    assert bilan['par_module'][0]['appels_30j'] == 41
    assert bilan['par_module'][1]['appels_7j'] == 0
    assert bilan['par_module'][1]['appels_30j'] == 10


def test_vidage_automatique_et_carte_exploitation(client, monkeypatch):
    """Au-delà de l'intervalle, le tampon se vide seul ; la page Exploitation affiche la carte sans nouvelle alerte."""
    monkeypatch.setattr(usage, 'INTERVALLE_VIDAGE_SECONDES', 0.0)
    _connecter(client, 'DIRECTEUR')
    titres_avant = [a['titre'] for a in exploitation.etat_exploitation()['alertes']]

    assert client.get(reverse('inscriptions:eleve_list')).status_code == 200
    assert UsageModuleQuotidien.objects.filter(module='inscriptions').exists()

    reponse = client.get(reverse('core:exploitation'))
    html = reponse.content.decode()
    assert reponse.status_code == 200
    assert 'Usage des modules (anonyme)' in html
    assert 'Élèves &amp; Inscriptions' in html or 'Élèves & Inscriptions' in html
    assert [a['titre'] for a in exploitation.etat_exploitation()['alertes']] == titres_avant
