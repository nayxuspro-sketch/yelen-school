"""
Manuels scolaires — filtres, garde-fous de suppression, cloisonnement des sélecteurs HTMX, historique par année,
information des parents (Lot J).
"""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from manuels.models import AttributionManuel, ExemplaireManuel, ManuelScolaire
from manuels.tests import monde  # noqa: F401 — fixture partagée

pytestmark = pytest.mark.django_db


def _attribuer(monde, exemplaire=None, inscription=None, **extra):  # noqa: F811
    exemplaire = exemplaire or baker.make(ExemplaireManuel, manuel=monde.manuel, etat='BON')
    return baker.make(AttributionManuel, exemplaire=exemplaire, inscription=inscription or monde.inscription,
                      date_attribution=date(2026, 10, 5), etat_sortie='BON', **extra)


def test_le_catalogue_se_filtre_par_cycle(monde):  # noqa: F811
    baker.make(ManuelScolaire, etablissement=monde.etab, titre='Lecture CP', cycle='PRIMAIRE')
    ManuelScolaire.objects.filter(pk=monde.manuel.pk).update(cycle='SECONDAIRE')
    html = monde.client.get(reverse('manuels:catalogue'), {'cycle': 'PRIMAIRE'}).content.decode()
    assert 'Lecture CP' in html and 'Mathématiques 6e' not in html
    html = monde.client.get(reverse('manuels:catalogue')).content.decode()
    assert 'Lecture CP' in html and 'Mathématiques 6e' in html


def test_un_manuel_retire_du_catalogue_n_apparait_plus(monde):  # noqa: F811
    ManuelScolaire.objects.filter(pk=monde.manuel.pk).update(actif=False)
    html = monde.client.get(reverse('manuels:catalogue')).content.decode()
    assert 'Mathématiques 6e' not in html


def test_detail_d_un_manuel_et_de_ses_exemplaires(monde):  # noqa: F811
    exemplaire = baker.make(ExemplaireManuel, manuel=monde.manuel, etat='NEUF')
    inactif = baker.make(ExemplaireManuel, manuel=monde.manuel, etat='USAGE', actif=False)
    reponse = monde.client.get(reverse('manuels:manuel_detail', kwargs={'pk': monde.manuel.pk}))
    assert reponse.status_code == 200
    assert list(reponse.context['exemplaires']) == [exemplaire]
    html = reponse.content.decode()
    assert exemplaire.code_exemplaire in html and inactif.code_exemplaire not in html
    assert monde.client.get(reverse('manuels:manuel_detail', kwargs={'pk': monde.etranger.pk})).status_code == 404


def test_un_manuel_avec_exemplaires_actifs_ne_peut_pas_etre_supprime(monde):  # noqa: F811
    baker.make(ExemplaireManuel, manuel=monde.manuel)
    reponse = monde.client.post(reverse('manuels:manuel_delete', kwargs={'pk': monde.manuel.pk}), follow=True)
    assert 'Impossible de supprimer un manuel ayant des exemplaires actifs.' in reponse.content.decode()
    monde.manuel.refresh_from_db()
    assert monde.manuel.actif


def test_modification_d_un_exemplaire(monde):  # noqa: F811
    exemplaire = baker.make(ExemplaireManuel, manuel=monde.manuel, etat='NEUF', annee_acquisition=2024)
    url = reverse('manuels:exemplaire_edit', kwargs={'manuel_pk': monde.manuel.pk, 'pk': exemplaire.pk})
    assert monde.client.get(url).status_code == 200
    reponse = monde.client.post(url, {'etat': 'USAGE', 'annee_acquisition': '2022'})
    assert reponse.status_code == 302
    exemplaire.refresh_from_db()
    assert exemplaire.etat == 'USAGE' and exemplaire.annee_acquisition == 2022
    assert ExemplaireManuel.objects.filter(manuel=monde.manuel).count() == 1, 'la modification ne crée rien'


def test_un_exemplaire_attribue_ne_peut_pas_etre_desactive(monde):  # noqa: F811
    attribution = _attribuer(monde)
    url = reverse('manuels:exemplaire_delete', kwargs={'manuel_pk': monde.manuel.pk, 'pk': attribution.exemplaire.pk})
    reponse = monde.client.post(url, follow=True)
    assert 'actuellement attribué à un élève' in reponse.content.decode()
    attribution.exemplaire.refresh_from_db()
    assert attribution.exemplaire.actif
    # Après retour, la désactivation passe
    AttributionManuel.objects.filter(pk=attribution.pk).update(date_retour=date(2027, 6, 1), etat_retour='BON')
    assert monde.client.post(url).status_code == 302
    attribution.exemplaire.refresh_from_db()
    assert not attribution.exemplaire.actif


def test_attribution_refusee_pour_un_eleve_ou_un_exemplaire_d_un_autre_etablissement(monde):  # noqa: F811
    exemplaire = baker.make(ExemplaireManuel, manuel=monde.manuel)
    exemplaire_etranger = baker.make(ExemplaireManuel, manuel=monde.etranger)
    autre_etab = monde.etranger.etablissement
    annee_autre = baker.make('parametres.AnneeScolaire', etablissement=autre_etab, libelle='2026-2027 bis', est_courante=True,
                             date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    insc_etrangere = baker.make('inscriptions.Inscription', annee_scolaire=annee_autre, statut='ACTIF',
                                classe=baker.make('parametres.Classe', etablissement=autre_etab, nom='6e Z'),
                                eleve=baker.make('inscriptions.Eleve', nom='AILLEURS', prenom='Sita', photo=''))
    url = reverse('manuels:attribution_create')
    base = {'date_attribution': '2026-10-05', 'etat_sortie': 'BON'}
    assert monde.client.post(url, {**base, 'exemplaire': str(exemplaire.pk), 'inscription': str(insc_etrangere.pk)}).status_code == 404
    assert monde.client.post(url, {**base, 'exemplaire': str(exemplaire_etranger.pk), 'inscription': str(monde.inscription.pk)}).status_code == 404
    assert not AttributionManuel.objects.exists()


def test_attribution_avec_date_par_defaut_et_etat_de_sortie(monde):  # noqa: F811
    exemplaire = baker.make(ExemplaireManuel, manuel=monde.manuel, etat='NEUF')
    reponse = monde.client.post(reverse('manuels:attribution_create'),
                                {'exemplaire': str(exemplaire.pk), 'inscription': str(monde.inscription.pk), 'etat_sortie': 'USAGE'})
    assert reponse.status_code == 302
    attribution = AttributionManuel.objects.get(exemplaire=exemplaire)
    assert attribution.date_attribution == date.today() and attribution.etat_sortie == 'USAGE'


def test_les_attributions_et_non_rendus_se_consultent_par_annee(monde):  # noqa: F811
    ancienne = baker.make('parametres.AnneeScolaire', etablissement=monde.etab, libelle='2025-2026', est_courante=False,
                          date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30))
    insc_ancienne = baker.make('inscriptions.Inscription', eleve=monde.inscription.eleve, classe=monde.classe,
                               annee_scolaire=ancienne, statut='ACTIF')
    ancien = baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire='MAT-ANC')
    _attribuer(monde, exemplaire=ancien, inscription=insc_ancienne)
    courant = baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire='MAT-CUR')
    _attribuer(monde, exemplaire=courant)
    for nom_url in ('manuels:attributions_list', 'manuels:non_rendus'):
        html = monde.client.get(reverse(nom_url)).content.decode()
        assert 'MAT-CUR' in html and 'MAT-ANC' not in html, nom_url
        html = monde.client.get(reverse(nom_url), {'annee': str(ancienne.pk)}).content.decode()
        assert 'MAT-ANC' in html and 'MAT-CUR' not in html, nom_url


def test_le_selecteur_d_eleves_ignore_une_classe_d_un_autre_etablissement(monde):  # noqa: F811
    autre_etab = monde.etranger.etablissement
    classe_etrangere = baker.make('parametres.Classe', etablissement=autre_etab, nom='6e Z')
    baker.make('inscriptions.Inscription', classe=classe_etrangere, annee_scolaire=monde.annee, statut='ACTIF',
               eleve=baker.make('inscriptions.Eleve', nom='AILLEURS', prenom='Sita', photo=''))
    html = monde.client.get(reverse('manuels:htmx_eleves'), {'classe': str(classe_etrangere.pk)}).content.decode()
    assert 'AILLEURS' not in html
    html = monde.client.get(reverse('manuels:attribution_create'), {'classe': str(classe_etrangere.pk)}).content.decode()
    assert 'AILLEURS' not in html


def test_le_selecteur_d_exemplaires_ne_propose_que_les_disponibles(monde):  # noqa: F811
    libre = baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire='MAT-LIBRE')
    pris = baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire='MAT-PRIS')
    _attribuer(monde, exemplaire=pris)
    html = monde.client.get(reverse('manuels:htmx_exemplaires'), {'manuel': str(monde.manuel.pk)}).content.decode()
    assert libre.code_exemplaire in html and pris.code_exemplaire not in html
    html = monde.client.get(reverse('manuels:htmx_exemplaires'), {'manuel': str(monde.etranger.pk)}).content.decode()
    assert 'EX-' not in html


def test_ecran_de_retour_et_retour_deja_effectue(monde):  # noqa: F811
    attribution = _attribuer(monde)
    url = reverse('manuels:attribution_retour', kwargs={'pk': attribution.pk})
    reponse = monde.client.get(url)
    assert reponse.status_code == 200 and 'TRAORE' in reponse.content.decode()
    reponse = monde.client.post(url, {'date_retour': '2027-06-15', 'etat_retour': 'DETERIORE', 'observation': 'Couverture arrachée'})
    assert reponse.status_code == 302
    attribution.refresh_from_db()
    attribution.exemplaire.refresh_from_db()
    assert attribution.etat_retour == 'DETERIORE' and attribution.observation == 'Couverture arrachée'
    assert attribution.exemplaire.etat == 'DETERIORE', "l'état de l'exemplaire suit l'état constaté au retour"
    assert monde.client.get(url).status_code == 404, 'un retour déjà enregistré ne se rejoue pas'


def test_facturation_impossible_sans_prix_de_remplacement(monde):  # noqa: F811
    ManuelScolaire.objects.filter(pk=monde.manuel.pk).update(prix_remplacement=Decimal('0'))
    attribution = _attribuer(monde)
    reponse = monde.client.post(reverse('manuels:facturer_non_rendu', kwargs={'pk': attribution.pk}), follow=True)
    assert 'Prix de remplacement non défini' in reponse.content.decode()
    attribution.refresh_from_db()
    assert not attribution.facture_genere and attribution.creance is None


def test_facturer_informe_le_parent_sur_le_portail(monde, settings, mocker):  # noqa: F811
    from core.models import Notification
    parent = baker.make('accounts.User', role='PARENT', etablissement=monde.etab, telephone='70000000', must_change_password=False)
    parent.eleves_lies.add(monde.inscription.eleve)
    settings.SMS_ENABLED = True
    envoi = mocker.patch('core.tasks.envoyer_sms_async')
    attribution = _attribuer(monde)
    assert monde.client.post(reverse('manuels:facturer_non_rendu', kwargs={'pk': attribution.pk})).status_code == 302
    notification = Notification.objects.get(destinataire=parent)
    assert notification.titre == 'Manuel non rendu — Mathématiques 6e' and '4,500 FCFA' in notification.message
    assert envoi.call_count == 1 and envoi.call_args.args[0] == '70000000'


def test_pdf_des_attributions_d_une_autre_annee(monde, mocker):  # noqa: F811
    weasy = mocker.patch('core.pdf.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    ancienne = baker.make('parametres.AnneeScolaire', etablissement=monde.etab, libelle='2025-2026', est_courante=False,
                          date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30))
    insc_ancienne = baker.make('inscriptions.Inscription', eleve=monde.inscription.eleve, classe=monde.classe,
                               annee_scolaire=ancienne, statut='ACTIF')
    _attribuer(monde, exemplaire=baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire='MAT-ANC'),
               inscription=insc_ancienne)
    reponse = monde.client.get(reverse('manuels:attributions_annee_pdf'), {'annee': str(ancienne.pk)})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert 'MAT-ANC' in weasy.call_args.kwargs['string']
