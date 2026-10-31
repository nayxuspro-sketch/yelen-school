"""Signataire des PDF (5.43.0) : détection du cycle/année, repli, mono/multi-signataires, signature scannée."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context
from model_bakery import baker

from documents.templatetags.signataire_tags import signataire_auto, signature_scannee, strip_article
from parametres.models import CoSignataire, SignataireDocument, TypeDocument

pytestmark = pytest.mark.django_db

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
       b'\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00'
       b'\x00IEND\xaeB`\x82')


@pytest.fixture
def cycle():
    etab = baker.make('etablissements.Etablissement')
    return baker.make('parametres.Cycle', etablissement=etab, code='PRIM')   # code de cycle : 4 caractères


@pytest.fixture
def annee(cycle):
    return baker.make('parametres.AnneeScolaire', etablissement=cycle.etablissement, est_courante=True)


@pytest.fixture
def membre(cycle):
    return baker.make('personnel.MembrePersonnel', etablissement=cycle.etablissement,
                      nom='OUÉDRAOGO', prenom='Issa')


@pytest.fixture
def bulletin():
    """Le catalogue est amorcé par migration : on réutilise BULLETIN plutôt que d'en créer un second."""
    return TypeDocument.objects.get_or_create(
        code='BULLETIN', defaults={'libelle': 'Bulletin de notes'})[0]


def _signataire(cycle, annee, membre, document, fonction='Le Directeur', **extra):
    return baker.make(SignataireDocument, cycle=cycle, annee_scolaire=annee, type_document=document,
                      membre_personnel_id=membre.pk, fonction=fonction, actif=True, **extra)


def test_strip_article_retire_l_article_initial():
    assert strip_article('Le Directeur des études') == 'Directeur des études'
    assert strip_article("L'Intendant") == 'Intendant'
    assert strip_article('Censeur') == 'Censeur'
    assert strip_article('') == '' and strip_article(None) is None


def test_sans_signataire_configure_le_bloc_est_vide():
    assert signataire_auto(Context({}), 'BULLETIN') == ''


def test_signataire_unique_aligne_a_droite(cycle, annee, membre, bulletin):
    _signataire(cycle, annee, membre, bulletin)
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=cycle.etablissement, ville='Ouagadougou')
    html = signataire_auto(Context({'annee_scolaire': annee, 'identite': identite}), 'BULLETIN')
    assert 'Ouagadougou,' in html and 'Le Directeur' in html
    assert 'OUÉDRAOGO Issa' in html and 'class="msig-zone" style="text-align:right;"' in html
    assert '<table class="msig-table"' not in html


def test_le_cycle_est_deduit_de_l_inscription(cycle, annee, membre, bulletin):
    """Sans contexte de cycle explicite, la signature vient de la classe de l'élève (cycle primaire)."""
    _signataire(cycle, annee, membre, bulletin)
    classe = baker.make('parametres.Classe', etablissement=cycle.etablissement, cycle=cycle)
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)
    html = signataire_auto(Context({'inscription': inscription}), 'BULLETIN')
    assert 'OUÉDRAOGO Issa' in html


def test_deux_signataires_sont_places_cote_a_cote(cycle, annee, membre, bulletin):
    principal = _signataire(cycle, annee, membre, bulletin, fonction='Le Directeur')
    second = baker.make('personnel.MembrePersonnel', etablissement=cycle.etablissement,
                        nom='KABORÉ', prenom='Awa')
    baker.make(CoSignataire, signataire_principal=principal, membre_personnel_id=second.pk,
               fonction='Le Censeur', ordre=1, actif=True)
    html = signataire_auto(Context({'annee_scolaire': annee}), 'BULLETIN')
    assert html.count('class="msig-col"') == 2
    assert 'OUÉDRAOGO Issa' in html and 'KABORÉ Awa' in html
    assert 'text-align:left' in html and 'text-align:right' in html


def test_variante_cellule_donne_fonction_et_nom_sans_date(cycle, annee, membre, bulletin):
    _signataire(cycle, annee, membre, bulletin, fonction='Le Proviseur')
    html = signataire_auto(Context({'annee_scolaire': annee}), 'BULLETIN', variante='cellule')
    assert 'msig-cellule' in html and 'Le Proviseur' in html and 'OUÉDRAOGO Issa' in html
    assert '<div class="msig-date"' not in html     # pas de « ville, le date » dans une case


def test_signature_scannee_rendue_si_le_membre_en_a_une(cycle, annee, membre, bulletin):
    membre.signature = SimpleUploadedFile('signature.png', PNG, content_type='image/png')
    membre.save(update_fields=['signature'])
    _signataire(cycle, annee, membre, bulletin)
    html = signataire_auto(Context({'annee_scolaire': annee}), 'BULLETIN')
    assert 'class="msig-img"' in html and 'signature' in html
    assert 'class="msig-img"' in signature_scannee(membre)
    assert signature_scannee(None) == ''


def test_un_type_de_document_inconnu_se_replie_sur_le_signataire_du_cycle(cycle, annee, membre, bulletin):
    _signataire(cycle, annee, membre, bulletin)
    html = signataire_auto(Context({'annee_scolaire': annee}), 'CERT_SCOL')
    assert 'OUÉDRAOGO Issa' in html


def test_une_erreur_de_rendu_ne_casse_pas_le_document(cycle, annee, membre, bulletin, mocker):
    mocker.patch.object(SignataireDocument.objects, 'get_signataire', side_effect=RuntimeError('boom'))
    assert signataire_auto(Context({'annee_scolaire': annee}), 'BULLETIN') == ''
