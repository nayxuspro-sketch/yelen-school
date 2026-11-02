"""Écrans de gestion des licences (couverture 5.47.1).

La licence conditionne l'accès de toute l'école : ces écrans sont réservés au Super Admin
(volet Système) ou au staff éditeur. Les tests couvrent la chaîne réelle — lister, créer,
activer, renouveler, révoquer — et les pages informatives vues par l'école.
"""
import datetime
from datetime import date, timedelta

import pytest
from django.urls import reverse
from model_bakery import baker

from licences.models import Licence, StatutLicence, TypeLicence

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    admin = baker.make('accounts.User', role='SUPER_ADMIN', is_superuser=True, is_staff=True,
                        etablissement=etab, must_change_password=False)
    licence = baker.make(Licence, etablissement=etab, type_licence=TypeLicence.PREMIUM, cle_licence='',
                         statut=StatutLicence.ACTIVE,
                         date_expiration=date.today() + timedelta(days=200),
                         date_activation=datetime.datetime.now(datetime.timezone.utc) - timedelta(days=100),
                         notes_interne='')
    client.force_login(admin)
    return {'client': client, 'etab': etab, 'admin': admin, 'licence': licence}


def _autre_licence(**extra):
    etab = baker.make('etablissements.Etablissement', nom='AILLEURS')
    champs = {'etablissement': etab, 'type_licence': TypeLicence.STARTER, 'cle_licence': '',
              'statut': StatutLicence.EN_ATTENTE,
              'date_expiration': date.today() + timedelta(days=365), 'notes_interne': ''}
    champs.update(extra)
    return baker.make(Licence, **champs)


# ── Tableau de bord ─────────────────────────────────────────────────────────

def test_gestion_licences_superuser_voit_tout_le_parc(ecole):
    """Un superuser voit toutes les licences, enrichies (jours restants, signature, limites)."""
    autre = _autre_licence()
    reponse = ecole['client'].get(reverse('licences:gestion'))
    assert reponse.status_code == 200
    licences = reponse.context['licences']
    assert {l['obj'].pk for l in licences} == {ecole['licence'].pk, autre.pk}
    mienne = next(l for l in licences if l['obj'].pk == ecole['licence'].pk)
    assert 190 <= mienne['jours_restants'] <= 201
    assert 0 <= mienne['jours_pct'] <= 100
    assert isinstance(mienne['signature_valide'], bool)
    assert mienne['limites'] == __import__('licences.models', fromlist=['LIMITES_LICENCES']) \
        .LIMITES_LICENCES[TypeLicence.PREMIUM]


def test_gestion_licences_admin_d_une_ecole_ne_voit_que_la_sienne(ecole):
    """Un Super Admin non-superuser ne voit que la licence de son établissement."""
    _autre_licence()
    ecole['admin'].is_superuser = False
    ecole['admin'].save(update_fields=['is_superuser'])
    reponse = ecole['client'].get(reverse('licences:gestion'))
    assert [l['obj'].pk for l in reponse.context['licences']] == [ecole['licence'].pk]
    assert reponse.context['is_superuser'] is False


def test_gestion_licences_sans_licence_ni_etablissement(ecole):
    """Un établissement sans licence, ou un compte sans établissement, affiche une liste vide."""
    Licence.objects.all().delete()
    reponse = ecole['client'].get(reverse('licences:gestion'))
    assert reponse.context['licences'] == []

    ecole['admin'].etablissement = None
    ecole['admin'].save(update_fields=['etablissement'])
    reponse = ecole['client'].get(reverse('licences:gestion'))
    assert reponse.context['licences'] == []


def test_gestion_licences_reservee_au_super_admin(ecole):
    """Un directeur d'école n'entre pas dans le volet Système : renvoyé à l'accueil."""
    ecole['client'].force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=ecole['etab'],
                                           must_change_password=False))
    reponse = ecole['client'].get(reverse('licences:gestion'))
    assert reponse.status_code == 302 and reponse.url.startswith('/?next=')


# ── Création / modification (staff éditeur) ─────────────────────────────────

def test_licence_create_puis_edit(ecole):
    """Créer une licence pour un établissement libre, refuser une date passée, puis modifier."""
    libre = baker.make('etablissements.Etablissement', nom='NOUVEAU')
    url = reverse('licences:licence_create')

    passee = ecole['client'].post(url, {'etablissement': str(libre.pk), 'type_licence': TypeLicence.STANDARD,
                                        'date_expiration': (date.today() - timedelta(days=1)).isoformat()})
    assert passee.status_code == 200 and 'date_expiration' in passee.context['form'].errors
    assert not Licence.objects.filter(etablissement=libre).exists()

    creation = ecole['client'].post(url, {'etablissement': str(libre.pk), 'type_licence': TypeLicence.STANDARD,
                                          'date_expiration': (date.today() + timedelta(days=90)).isoformat(),
                                          'notes_interne': 'Essai'})
    assert creation.status_code == 302 and creation.url == reverse('licences:gestion')
    nouvelle = Licence.objects.get(etablissement=libre)
    assert nouvelle.cle_licence.startswith('YELEN-')

    formulaire = ecole['client'].get(reverse('licences:licence_edit', kwargs={'pk': nouvelle.pk}))
    assert formulaire.status_code == 200 and formulaire.context['licence'] == nouvelle

    modification = ecole['client'].post(
        reverse('licences:licence_edit', kwargs={'pk': nouvelle.pk}),
        {'etablissement': str(libre.pk), 'type_licence': TypeLicence.PREMIUM,
         'date_expiration': (date.today() + timedelta(days=300)).isoformat(), 'notes_interne': 'Confirmé'})
    assert modification.status_code == 302
    nouvelle.refresh_from_db()
    assert nouvelle.type_licence == TypeLicence.PREMIUM and nouvelle.notes_interne == 'Confirmé'


def test_licence_create_refuse_un_doublon_d_etablissement(ecole):
    """Un établissement possède une seule licence : le formulaire le dit au lieu de planter."""
    reponse = ecole['client'].post(reverse('licences:licence_create'),
                                   {'etablissement': str(ecole['etab'].pk), 'type_licence': TypeLicence.STANDARD,
                                    'date_expiration': (date.today() + timedelta(days=90)).isoformat()})
    assert reponse.status_code == 200
    assert 'existe déjà' in str(reponse.context['form'].errors)


# ── Activer / renouveler / révoquer ────────────────────────────────────────

def test_licence_activer_puis_refus_de_rejouer(ecole):
    """Activer une licence en attente accorde l'accès ; une licence déjà active n'est pas réactivée."""
    licence = _autre_licence()
    url = reverse('licences:licence_activer', kwargs={'pk': licence.pk})
    assert ecole['client'].get(url).status_code == 200

    ecole['client'].post(url, {})
    licence.refresh_from_db()
    assert licence.statut == StatutLicence.ACTIVE and licence.date_activation is not None
    assert licence.date_debut_periode == licence.date_activation.date()

    deja = ecole['client'].post(url, {}, follow=True)
    assert 'Activation impossible' in deja.content.decode()


def test_licence_renouveler_allonge_l_expiration(ecole):
    """Le renouvellement repousse l'expiration de la durée choisie et repart sur une période."""
    licence = _autre_licence(statut=StatutLicence.ACTIVE,
                             date_expiration=date.today() + timedelta(days=10))
    url = reverse('licences:licence_renouveler', kwargs={'pk': licence.pk})
    assert ecole['client'].get(url).status_code == 200

    reponse = ecole['client'].post(url, {'duree_jours': '365'})
    assert reponse.status_code == 302
    licence.refresh_from_db()
    assert licence.date_expiration >= date.today() + timedelta(days=364)
    assert licence.statut == StatutLicence.ACTIVE


def test_licence_revoquer_exige_un_motif_puis_verrouille(ecole):
    """La révocation documente son motif dans la licence et n'est jamais rejouée."""
    licence = _autre_licence(statut=StatutLicence.ACTIVE)
    url = reverse('licences:licence_revoquer', kwargs={'pk': licence.pk})
    assert ecole['client'].get(url).status_code == 200

    sans_motif = ecole['client'].post(url, {'raison': '', 'confirmation': 'on'})
    assert sans_motif.status_code == 200 and 'raison' in sans_motif.context['form'].errors
    licence.refresh_from_db()
    assert licence.statut == StatutLicence.ACTIVE

    sans_confirmation = ecole['client'].post(url, {'raison': 'Impayé 2026'})
    assert sans_confirmation.status_code == 200 and 'confirmation' in sans_confirmation.context['form'].errors
    licence.refresh_from_db()
    assert licence.statut == StatutLicence.ACTIVE

    ecole['client'].post(url, {'raison': 'Impayé 2026', 'confirmation': 'on'})
    licence.refresh_from_db()
    assert licence.statut == StatutLicence.REVOQUEE and 'Impayé 2026' in licence.notes_interne

    encore = ecole['client'].post(url, {}, follow=True)
    assert 'déjà révoquée' in encore.content.decode()


def test_ecrans_de_gestion_reserves_au_staff(ecole):
    """Un compte non-staff de l'école n'atteint pas les écrans d'édition de licence."""
    ecole['client'].force_login(baker.make('accounts.User', role='SECRETAIRE', etablissement=ecole['etab'],
                                           must_change_password=False))
    for nom, kwargs in (('licence_create', {}),
                        ('licence_edit', {'pk': ecole['licence'].pk}),
                        ('licence_activer', {'pk': ecole['licence'].pk}),
                        ('licence_renouveler', {'pk': ecole['licence'].pk}),
                        ('licence_revoquer', {'pk': ecole['licence'].pk}),
                        ('outils', {})):
        reponse = ecole['client'].get(reverse(f'licences:{nom}', kwargs=kwargs))
        assert reponse.status_code == 302 and reponse.url.startswith('/?next='), nom


# ── Pages informatives ─────────────────────────────────────────────────────

def test_pages_activer_renouveler_statut_support_guide(ecole):
    """Les pages vues par l'école répondent et portent le bon diagnostic."""
    activation = ecole['client'].get(reverse('licences:activer'))
    assert activation.status_code == 200
    assert activation.context['etab'] == ecole['etab']
    assert activation.context['est_super_admin'] is True
    assert activation.context['motif_invalide'] is None, 'la licence est valide'
    assert activation.context['empreinte_serveur']

    renouvellement = ecole['client'].get(reverse('licences:renouveler'))
    assert renouvellement.status_code == 200
    assert renouvellement.context['est_expiree'] is False
    assert renouvellement.context['jours_restants'] > 0

    abonnement = ecole['client'].get(reverse('licences:statut'))
    assert abonnement.status_code == 200
    assert abonnement.context['est_expiree'] is False and abonnement.context['expire_bientot'] is False
    assert abonnement.context['features_rows'] and all('label' in r for r in abonnement.context['features_rows'])
    assert abonnement.context['is_superuser'] is True

    assert ecole['client'].get(reverse('licences:support')).status_code == 200
    assert ecole['client'].get(reverse('licences:guide')).status_code == 200


def test_motif_licence_invalide_explique_chaque_situation(ecole, settings):
    """L'école comprend pourquoi sa licence ne passe pas : signature, date, statut, absence."""
    from licences.views import _motif_licence_invalide

    assert _motif_licence_invalide(None).startswith("Aucune licence")
    licence = ecole['licence']
    licence.date_expiration = date.today() - timedelta(days=5)
    licence.save(update_fields=['date_expiration'])
    assert 'expiré le' in _motif_licence_invalide(licence)

    licence.date_expiration = date.today() + timedelta(days=30)
    licence.statut = StatutLicence.EN_ATTENTE
    licence.save(update_fields=['date_expiration', 'statut'])
    assert _motif_licence_invalide(licence).startswith('Statut de la licence')

    # Signature altérée en base (fraude ou corruption) : la licence n'est plus reconnue.
    Licence.objects.filter(pk=licence.pk).update(signature_hmac='0' * 64)
    licence.refresh_from_db()
    assert _motif_licence_invalide(licence).startswith("La licence enregistrée n'est pas reconnue")

    # Licence liée à un autre serveur quand le liage est exigé.
    licence.save()                                  # resigne correctement
    licence.statut = StatutLicence.ACTIVE
    licence.empreinte_serveur = 'empreinte-d-un-autre-serveur'
    licence.save()
    settings.LICENCE_BINDING_ENABLED = True
    assert _motif_licence_invalide(licence) == 'La licence a été émise pour un autre serveur.'


def test_statut_signale_une_licence_expiree_ou_proche_du_terme(ecole):
    """« Mon abonnement » alerte avant l'expiration, et distingue une licence périmée."""
    ecole['licence'].date_expiration = date.today() + timedelta(days=10)
    ecole['licence'].save(update_fields=['date_expiration'])
    bientot = ecole['client'].get(reverse('licences:statut'))
    assert bientot.context['expire_bientot'] is True and bientot.context['est_expiree'] is False

    ecole['licence'].date_expiration = date.today() - timedelta(days=2)
    ecole['licence'].save(update_fields=['date_expiration'])
    expiree = ecole['client'].get(reverse('licences:statut'))
    assert expiree.context['est_expiree'] is True
    assert ecole['client'].get(reverse('licences:renouveler')).context['est_expiree'] is True


def test_ecole_sans_licence_reste_informee(ecole):
    """Sans licence, les pages d'information répondent quand même (aucun 500)."""
    Licence.objects.all().delete()
    assert ecole['client'].get(reverse('licences:statut')).status_code == 200
    renouvellement = ecole['client'].get(reverse('licences:renouveler'))
    assert renouvellement.context['licence'] is None and renouvellement.context['est_expiree'] is False
    assert ecole['client'].get(reverse('licences:support')).context['statut_display'] is None


# ── Activation par jeton ───────────────────────────────────────────────────

def test_activer_par_jeton_reussi(ecole, mocker):
    """Un jeton accepté active la licence, réinitialise l'état de démarrage et renvoie à l'abonnement."""
    mocker.patch('licences.services.activer_jeton', return_value=ecole['licence'])
    reinit = mocker.patch('licences.boot_check.reinitialiser_etat_boot')

    reponse = ecole['client'].post(reverse('licences:activer'), {'jeton': 'YELEN-JETON-VALIDE'})
    assert reponse.status_code == 302 and reponse.url == reverse('licences:statut')
    reinit.assert_called_once()


def test_activer_par_jeton_refuse_est_explique(ecole, mocker):
    """Un jeton invalide ne modifie rien et affiche la raison du refus."""
    from licences.jeton import JetonInvalide
    mocker.patch('licences.services.activer_jeton', side_effect=JetonInvalide('signature invalide'))
    reinit = mocker.patch('licences.boot_check.reinitialiser_etat_boot')

    reponse = ecole['client'].post(reverse('licences:activer'), {'jeton': 'faux'}, follow=True)
    assert 'Activation refusée' in reponse.content.decode()
    assert 'signature invalide' in reponse.content.decode()
    reinit.assert_not_called()


def test_activer_est_reserve_au_super_admin_et_exige_un_etablissement(ecole):
    """Un directeur ne peut pas poster un jeton ; un compte sans établissement est renvoyé."""
    ecole['client'].force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=ecole['etab'],
                                           must_change_password=False))
    assert ecole['client'].post(reverse('licences:activer'), {'jeton': 'x'}).status_code == 403

    ecole['admin'].etablissement = None
    ecole['admin'].save(update_fields=['etablissement'])
    ecole['client'].force_login(ecole['admin'])
    reponse = ecole['client'].post(reverse('licences:activer'), {'jeton': 'x'}, follow=True)
    assert 'aucun établissement' in reponse.content.decode()


# ── Outils cryptographiques (développement) ────────────────────────────────

def test_outils_licence_generent_une_cle(ecole):
    """L'outil de développement génère une clé YELEN-XXXX-XXXX-XXXX et sa signature d'intégrité."""
    url = reverse('licences:outils')
    assert ecole['client'].get(url).status_code == 200

    sans_type = ecole['client'].post(url, {'action': 'generer', 'etablissement_id': str(ecole['etab'].pk)})
    assert sans_type.context['erreur'] == 'Type de licence invalide.'

    sans_etab = ecole['client'].post(url, {'action': 'generer', 'type_licence': TypeLicence.PREMIUM})
    assert sans_etab.context['erreur'] == "Identifiant d'établissement requis."

    genere = ecole['client'].post(url, {'action': 'generer', 'type_licence': TypeLicence.PREMIUM,
                                        'etablissement_id': str(ecole['etab'].pk)})
    resultat = genere.context['resultat']
    assert resultat['cle'].startswith('YELEN-') and len(resultat['cle']) == 20
    assert resultat['type_licence'] == TypeLicence.PREMIUM and resultat['etab_id'] == str(ecole['etab'].pk)
    assert len(resultat['signature_hmac']) == 64


def test_outils_licence_verifient_une_licence_existante(ecole):
    """La vérification compare la signature stockée et la signature recalculée."""
    url = reverse('licences:outils')
    incomplet = ecole['client'].post(url, {'action': 'verifier', 'cle_licence': 'YELEN-1'})
    assert incomplet.context['erreur'] == 'Tous les champs sont requis pour la vérification.'

    date_invalide = ecole['client'].post(url, {'action': 'verifier', 'cle_licence': 'YELEN-AAAA-BBBB-CCCC',
                                              'type_licence_v': TypeLicence.PREMIUM,
                                              'date_expiration': '31/12/2027'})
    assert 'Format de date invalide' in date_invalide.context['erreur']

    en_base = ecole['client'].post(url, {'action': 'verifier', 'cle_licence': ecole['licence'].cle_licence,
                                         'type_licence_v': ecole['licence'].type_licence,
                                         'date_expiration': ecole['licence'].date_expiration.isoformat()})
    assert en_base.context['resultat']['en_base'] is True
    assert en_base.context['resultat']['lic_db'] == ecole['licence']

    inconnue = ecole['client'].post(url, {'action': 'verifier', 'cle_licence': 'YELEN-ZZZZ-ZZZZ-ZZZZ',
                                          'type_licence_v': TypeLicence.STARTER,
                                          'date_expiration': '2027-12-31'})
    assert inconnue.context['resultat']['en_base'] is False
    assert inconnue.context['resultat']['valide_db'] is None

    inconnu = ecole['client'].post(url, {'action': 'n_importe_quoi'})
    assert inconnu.context['erreur'] == 'Action inconnue.'


def test_outils_licence_disparaissent_quand_le_controle_est_actif(ecole, settings):
    """En production (contrôle actif), l'outil qui expose l'algorithme de signature renvoie 404."""
    settings.LICENSE_ENFORCEMENT = True
    reponse = ecole['client'].get(reverse('licences:outils'))
    assert reponse.status_code == 404
