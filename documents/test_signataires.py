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


# ── Liste générale des élèves : signature du directeur général ──────────────────────────────────
# La liste couvre toutes les classes : elle n'a ni cycle ni classe dont déduire un signataire, alors que
# les signataires se configurent cycle par cycle. Elle était donc signée par le dernier signataire
# modifié, quel qu'il soit (souvent un directeur de cycle ou le comptable des reçus).


@pytest.fixture
def etablissement_avec_directeur_general(cycle):
    """Directeur général désigné sur la fiche du personnel, plus un signataire de cycle plus récent."""
    etab = cycle.etablissement
    dg = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='OUÉDRAOGO', prenom='Issa',
                    fonction='Directeur général', est_directeur=True, is_active=True)
    dg.signature = SimpleUploadedFile('dg.png', PNG, content_type='image/png')
    dg.save(update_fields=['signature'])
    return etab, dg


def test_liste_des_eleves_signee_par_le_directeur_general(cycle, annee, etablissement_avec_directeur_general):
    """Le directeur général signe la liste générale des élèves, avec sa signature scannée."""
    from documents.templatetags.signataire_tags import signataire_directeur_general
    etab, dg = etablissement_avec_directeur_general
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=etab, ville='Ouagadougou',
                          nom_directeur='Nom saisi sur la fiche établissement')
    contexte = Context({'identite': identite, 'etablissement': etab, 'annee_scolaire': annee})

    html = signataire_directeur_general(contexte)

    assert 'OUÉDRAOGO Issa' in html and 'Directeur général' in html
    assert 'class="msig-img"' in html and 'class="msig-zone" style="text-align:right;"' in html
    assert 'Ouagadougou, le' in html
    assert 'f-établissement' not in html          # le nom de la fiche ne prime jamais sur le directeur général


def test_liste_des_eleves_ignore_le_signataire_de_cycle_le_plus_recent(cycle, annee, etablissement_avec_directeur_general):
    """Un signataire de cycle modifié après la désignation du directeur général ne signe pas la liste."""
    from documents.templatetags.signataire_tags import signataire_directeur_general
    etab, dg = etablissement_avec_directeur_general
    autre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORÉ', prenom='Salimata')
    _signataire(cycle, annee, autre, TypeDocument.objects.get_or_create(
        code='LISTE_CLASSE', defaults={'libelle': 'Liste Alphabétique de Classe'})[0], fonction='Le Censeur')

    html = signataire_directeur_general(Context({'etablissement': etab, 'annee_scolaire': annee}))

    assert 'OUÉDRAOGO Issa' in html and 'KABORÉ Salimata' not in html


def test_liste_des_eleves_sans_directeur_general_utilise_le_nom_de_la_fiche(cycle, annee):
    """Aucun directeur général désigné : repli sur le nom de la fiche de l'établissement, sans signature."""
    from documents.templatetags.signataire_tags import signataire_directeur_general
    etab = cycle.etablissement
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=etab, ville='Koudougou',
                          nom_directeur='Issa OUÉDRAOGO')

    html = signataire_directeur_general(Context({'identite': identite, 'annee_scolaire': annee}))

    assert 'Issa OUÉDRAOGO' in html and 'Koudougou, le' in html
    assert 'class="msig-img"' not in html and 'class="msig-sign"></div>' in html


def test_liste_des_eleves_sans_directeur_general_utilise_le_type_liste_eleves(cycle, annee):
    """Sans directeur général désigné, le titulaire du type « Liste des élèves » prime sur le nom de la fiche."""
    from documents.templatetags.signataire_tags import signataire_directeur_general
    etab = cycle.etablissement
    type_doc, _ = TypeDocument.objects.get_or_create(
        code='LISTE_ELEVES', defaults={'libelle': 'Liste des Élèves', 'categorie': 'SCOLARITE'})
    signataire = _signataire(cycle, annee, baker.make('personnel.MembrePersonnel', etablissement=etab,
                                                      nom='TRAORÉ', prenom='Awa'),
                             type_doc, fonction='Le Proviseur')
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_directeur='Nom de repli')

    html = signataire_directeur_general(Context({'identite': identite, 'annee_scolaire': annee}))

    assert 'TRAORÉ Awa' in html and 'Le Proviseur' in html
    assert 'Nom de repli' not in html
    assert signataire.get_membre_personnel().nom == 'TRAORÉ'


def test_liste_des_eleves_sans_aucune_source_ne_rend_rien(cycle, annee):
    from documents.templatetags.signataire_tags import signataire_directeur_general
    assert signataire_directeur_general(Context({})) == ''
    assert signataire_directeur_general(
        Context({'etablissement': cycle.etablissement, 'annee_scolaire': annee})) == ''


def test_liste_des_eleves_variante_cellule(cycle, annee, etablissement_avec_directeur_general):
    from documents.templatetags.signataire_tags import signataire_directeur_general
    etab, dg = etablissement_avec_directeur_general
    html = signataire_directeur_general(
        Context({'etablissement': etab, 'annee_scolaire': annee}), variante='cellule')
    assert 'msig-cellule' in html and 'OUÉDRAOGO Issa' in html
    assert '<div class="msig-date"' not in html

def test_export_pdf_de_la_liste_des_eleves_imprime_le_directeur_general(client, cycle, annee, monkeypatch):
    """Bout en bout : le PDF « Liste des élèves » (toutes classes) est signé par la direction générale,
    jamais par le signataire d'un cycle.

    Le gabarit portait le type « Liste Alphabétique de Classe », configuré cycle par cycle : sur une
    liste qui couvre toutes les classes, la résolution n'avait aucun cycle et retombait sur le dernier
    signataire modifié, quel qu'il soit — d'où une signature de directeur de cycle.
    """
    from django.urls import reverse
    from inscriptions.models import Inscription
    from inscriptions.views import eleves as vues_eleves

    etab = cycle.etablissement
    dg = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='OUÉDRAOGO', prenom='Issa',
                    fonction='Directeur général', est_directeur=True, is_active=True)
    dg.signature = SimpleUploadedFile('dg.png', PNG, content_type='image/png')
    dg.save(update_fields=['signature'])
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, ville='Ouagadougou',
               nom_directeur='Nom de la fiche établissement')

    # Un signataire de cycle plus récent : il signe les listes de classe, pas la liste générale.
    type_classe = TypeDocument.objects.get_or_create(
        code='LISTE_CLASSE', defaults={'libelle': 'Liste Alphabétique de Classe'})[0]
    _signataire(cycle, annee, baker.make('personnel.MembrePersonnel', etablissement=etab,
                                        nom='KABORÉ', prenom='Salimata'),
                type_classe, fonction='Le Censeur')

    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    eleve = baker.make('inscriptions.Eleve', nom='TRAORÉ', prenom='Awa')
    baker.make(Inscription, eleve=eleve, classe=classe, annee_scolaire=annee)

    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True,
                                  must_change_password=False))
    sources = []

    class HTMLSansRendu:
        def __init__(self, *args, **kwargs):
            sources.append(kwargs['string'])

        def write_pdf(self, *args, **kwargs):
            return b'%PDF-1.7 test'

    monkeypatch.setattr(vues_eleves, '_WeasyHTML', HTMLSansRendu)
    reponse = client.get(reverse('inscriptions:eleve_list_pdf'))

    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    html = sources[0]
    assert 'OUÉDRAOGO Issa' in html and 'Directeur général' in html
    assert 'KABORÉ Salimata' not in html and 'Nom de la fiche établissement' not in html
