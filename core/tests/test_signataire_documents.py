"""Chaque document PDF imprime le signataire configuré — fonction, signature scannée, NOM Prénom.

Documents dont la case « Le Directeur » restait manuscrite, ou qui n'avaient aucune signature, jusqu'en 5.5.13 :
contrat de travail, bulletin de salaire, bulletin de vacation, PV de conseil, dossier de transfert, bulletin de
compétences, liste des élèves, liste des candidats, liste des boursiers, documents manuels scolaires.
Le garde-fou statique (test_pdf_base) impose le tag à tout gabarit PDF ; ce test prouve le rendu réel.
"""
import datetime
import io
from decimal import Decimal

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from model_bakery import baker

from parametres.models import SignataireDocument, TypeDocument

pytestmark = pytest.mark.django_db


def _png():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (120, 40), (10, 10, 120)).save(buffer, 'PNG')
    return buffer.getvalue()


def _texte_et_images(document):
    from weasyprint.formatting_structure import boxes
    textes, images = [], []

    def parcourir(box):
        if isinstance(box, boxes.TextBox):
            textes.append(box.text)
        if isinstance(box, boxes.ReplacedBox) and box.element_tag == 'img':
            images.append(box.element.get('class', ''))
        for enfant in getattr(box, 'children', ()):
            parcourir(enfant)

    for page in document.pages:
        parcourir(page._page_box)
    return ' '.join(textes), images


@pytest.fixture
def monde(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR', sigle='LS',
               type_etablissement='PRIVE', numero_agrement_mena='AG-1', adresse_complete='Rue 1', ville='Ouagadougou',
               province='Kadiogo', region='Centre', telephone='70000000', email='x@y.bf')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Secondaire', ordre=1)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='6EME', nom='6e A')
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Nouveau')
    eleve = baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Awa', genre='F',
                       date_naissance=datetime.date(2014, 5, 2), photo='', matricule='E-001')
    insc = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut_eleve=statut)
    trim = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1,
                      date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2026, 12, 20))
    directeur = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Issouf',
                           email='kabore@y.bf', photo='', is_active=True)
    directeur.signature.save('directeur.png', ContentFile(_png()), save=True)
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Ali',
                      email='zongo@y.bf', photo='', is_active=True)
    prof.signature.save('prof.png', ContentFile(_png()), save=True)
    for type_doc in TypeDocument.objects.filter(actif=True):
        SignataireDocument.objects.create(cycle=cycle, type_document=type_doc, annee_scolaire=annee,
                                          membre_personnel_id=directeur.id, fonction='Le Directeur', actif=True)
    matiere = baker.make('pedagogie.Matiere', code='MATH', nom='Mathématiques', coefficient=Decimal('3'))
    ens = baker.make('pedagogie.Enseignement', matiere=matiere, classe=classe, annee_scolaire=annee,
                     personnel=prof, coefficient=Decimal('3'), est_actif=True)
    user = baker.make('accounts.User', etablissement=etab, is_superuser=True, is_staff=True,
                      must_change_password=False, role='DIRECTEUR')
    salaire = baker.make('personnel.SalairePersonnel', personnel=prof, annee_scolaire=annee, mois=10)
    vacation = baker.make('vacations.BulletinVacation', personnel=prof, annee_scolaire=annee, mois=10, annee=2026)
    conseil = baker.make('viescolaire.ConseilClasse', classe=classe, trimestre=trim, president=user,
                         date_conseil=datetime.date(2026, 12, 20))
    transfert = baker.make('inscriptions.TransfertEleve', inscription=insc, etablissement_destination='Lycée X',
                           date_demande=datetime.date(2026, 11, 2))
    session = baker.make('examens.SessionExamen', annee_scolaire=annee, type_examen='BEPC')
    return dict(user=user, annee=annee, classe=classe, insc=insc, trim=trim, prof=prof, ens=ens, salaire=salaire,
                vacation=vacation, conseil=conseil, transfert=transfert, session=session)


DOCUMENTS = {
    'contrat_travail': lambda m: reverse('personnel:contrat', args=[m['prof'].pk]) + '?format=pdf',
    'bulletin_salaire': lambda m: reverse('personnel:salaire_detail', args=[m['salaire'].pk]) + '?format=pdf',
    'bulletin_vacation': lambda m: reverse('vacations:bulletin_vacation_pdf', args=[m['vacation'].pk]),
    'pv_conseil': lambda m: reverse('viescolaire:conseil_pv_pdf', args=[m['conseil'].pk]),
    'dossier_transfert': lambda m: reverse('inscriptions:transfert_inter_dossier_pdf', args=[m['transfert'].pk]),
    'bulletin_competences': lambda m: reverse('pedagogie:competences_bulletin_pdf', args=[m['insc'].pk, m['trim'].pk]),
    'liste_eleves': lambda m: reverse('inscriptions:eleve_list_pdf'),
    'liste_candidats': lambda m: reverse('examens:candidats_session_pdf', args=[m['session'].pk]),
    'liste_boursiers': lambda m: reverse('finances:boursiers_pdf'),
    'manuels_inventaire': lambda m: reverse('manuels:inventaire_classe_pdf', args=[m['classe'].pk]),
    'manuels_attributions': lambda m: reverse('manuels:attributions_annee_pdf'),
    'manuels_non_rendus': lambda m: reverse('manuels:non_rendus_pdf'),
}


def _rendre(client, monkeypatch, monde, url):
    """Rend le document avec WeasyPrint et retourne (texte des pages, classes des <img> réellement rendues)."""
    from core.pdf import HTML
    rendus = []
    original = HTML.render

    def espion(self, *args, **kwargs):
        document = original(self, *args, **kwargs)
        rendus.append(document)
        return document

    monkeypatch.setattr(HTML, 'render', espion)
    client.force_login(monde['user'])
    reponse = client.get(url)
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf', url
    assert rendus, url
    texte, images = _texte_et_images(rendus[0])
    return texte, images


@pytest.mark.parametrize('document', sorted(DOCUMENTS))
def test_le_signataire_configure_est_imprime(client, monkeypatch, monde, document):
    texte, images = _rendre(client, monkeypatch, monde, DOCUMENTS[document](monde))
    assert 'Le Directeur' in texte and 'KABORE Issouf' in texte, document
    assert 'msig-img' in images, document


def test_fiche_de_discipline_signature_scannee_de_l_enseignant(client, monkeypatch, monde):
    """La fiche de discipline est certifiée par l'enseignant : c'est sa signature scannée qui s'imprime."""
    m = monde
    url = (reverse('pedagogie:fiche_discipline_pdf')
           + f"?annee={m['annee'].pk}&classe={m['classe'].pk}&enseignement={m['ens'].pk}&periode={m['trim'].pk}")
    texte, images = _rendre(client, monkeypatch, monde, url)
    assert 'ZONGO ALI' in texte and 'KABORE' not in texte  # nom en capitales (text-transform du gabarit)
    assert 'msig-img' in images
