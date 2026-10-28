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
    paiement = baker.make('finances.Paiement', inscription=insc, montant=Decimal('25000'), reference='R-1',
                          observation='', mode_paiement='ESPECES', date_paiement=datetime.date(2026, 10, 5))
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCO', actif=True)
    baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, statut_eleve=statut, rubrique=rubrique,
               annee_scolaire=annee, montant=Decimal('150000'), actif=True)
    conge = baker.make('personnel.CongePersonnel', personnel=prof, date_debut=datetime.date(2026, 11, 2),
                       date_fin=datetime.date(2026, 11, 6))
    baker.make('viescolaire.SeanceCours', enseignement=ens, jour=1, heure_debut=datetime.time(8, 0),
               heure_fin=datetime.time(10, 0), salle='S1')
    baker.make('pedagogie.MoyenneGenerale', inscription=insc, trimestre=trim, moyenne=Decimal('12.50'),
               moyenne_sur_20=Decimal('12.50'), rang=1)
    return dict(user=user, etab=etab, annee=annee, cycle=cycle, classe=classe, insc=insc, trim=trim, prof=prof, ens=ens,
                salaire=salaire, vacation=vacation, conseil=conseil, transfert=transfert, session=session,
                paiement=paiement, rubrique=rubrique, conge=conge)


def _post_convocation(client, m):
    return client.post(reverse('documents:convocation_form'), {
        'classe': str(m['classe'].pk), 'inscriptions': [str(m['insc'].pk)], 'type_convocation': 'AUTRE',
        'date_convocation': '2026-11-10', 'heure_convocation': '08:00', 'lieu': 'Bureau', 'objet': 'Entretien',
        'corps': 'Merci de vous présenter.', 'format': 'pdf',
    })


def _post_circulaire(client, m):
    return client.post(reverse('documents:circulaire_form'), {
        'titre': 'Rentrée', 'objet': 'Organisation', 'corps': 'Texte.', 'date_circulaire': '2026-11-10',
        'classes': [str(m['classe'].pk)], 'format': 'pdf',
    })


# Tous les documents PDF signés de l'application (les non signés sont listés dans test_pdf_base.SANS_SIGNATAIRE)
DOCUMENTS = {
    'certificat_scolarite': lambda m: reverse('documents:certificat_scolarite', args=[m['insc'].pk]) + '?format=pdf',
    'attestation_non_redevabilite': lambda m: reverse('documents:attestation_non_redevabilite', args=[m['insc'].pk]) + '?format=pdf',
    'convocation': _post_convocation,
    'circulaire': _post_circulaire,
    'liste_classe': lambda m: reverse('documents:liste_classe_pdf', args=[m['classe'].pk]) + '?format=pdf',
    'liste_personnel_cycle': lambda m: reverse('documents:liste_personnel_pdf', args=[m['cycle'].pk]) + '?format=pdf',
    'liste_personnel_module': lambda m: reverse('personnel:personnel_list_pdf'),
    'carte_scolaire': lambda m: reverse('inscriptions:eleve_carte', args=[m['insc'].eleve_id]) + '?format=pdf',
    'fiche_eleve': lambda m: reverse('inscriptions:eleve_fiche_pdf', args=[m['insc'].eleve_id]),
    'cartes_classe': lambda m: reverse('inscriptions:classe_cartes_pdf', args=[m['classe'].pk]),
    'recu_paiement': lambda m: reverse('finances:recu_pdf', args=[m['paiement'].pk]),
    'historique_versements': lambda m: reverse('finances:historique_pdf', args=[m['insc'].pk]),
    'certificat_non_redevabilite': lambda m: reverse('finances:certificat_non_redevabilite', args=[m['insc'].pk]),
    'relance_paiement': lambda m: (reverse('finances:relance_paiement_pdf')
                                   + f"?annee={m['annee'].pk}&classe={m['classe'].pk}&rubrique={m['rubrique'].pk}"),
    'liste_redevables': lambda m: reverse('finances:liste_redevables_pdf'),
    'liste_exoneres': lambda m: reverse('finances:liste_exoneres_pdf'),
    'bilan_encaissements': lambda m: reverse('finances:bilan_encaissements_pdf'),
    'journal_caisse': lambda m: reverse('finances:journal_caisse_pdf') + '?date=2026-10-05&caissier=',
    'bulletin_trimestriel': lambda m: reverse('pedagogie:bulletin_pdf', args=[m['insc'].pk, m['trim'].pk]),
    'bulletin_duplicata': lambda m: reverse('pedagogie:bulletin_duplicata_pdf', args=[m['insc'].pk, m['trim'].pk]),
    'bulletins_classe_lot': lambda m: reverse('pedagogie:bulletin_classe_batch_pdf', args=[m['classe'].pk, m['trim'].pk]),
    'bulletin_annuel': lambda m: reverse('pedagogie:bulletin_annuel_pdf', args=[m['insc'].pk]),
    'bulletins_annuels_lot': lambda m: reverse('pedagogie:bulletin_annuel_classe_batch_pdf', args=[m['classe'].pk]),
    'bulletin_annuel_module': lambda m: reverse('bulletins:bulletin_annuel_pdf', args=[m['insc'].pk, m['annee'].pk]),
    'bulletins_annuels_module_lot': lambda m: reverse('bulletins:bulletin_annuel_batch_pdf', args=[m['classe'].pk, m['annee'].pk]),
    'palmares_annuel': lambda m: reverse('pedagogie:palmares_annuel_pdf', args=[m['classe'].pk]),
    'bilan_periodes': lambda m: reverse('pedagogie:bilan_pdf') + f"?annee={m['annee'].pk}&classe={m['classe'].pk}",
    'releve_moyenne_classe': lambda m: (reverse('pedagogie:releve_moyenne_classe_pdf')
                                        + f"?classe={m['classe'].pk}&trimestre={m['trim'].pk}"),
    'moyennes_disciplines': lambda m: (reverse('pedagogie:moyennes_disciplines_pdf')
                                       + f"?annee={m['annee'].pk}&trimestre={m['trim'].pk}&classe={m['classe'].pk}"),
    'releve_notes': lambda m: (reverse('pedagogie:releve_notes_pdf')
                               + f"?annee={m['annee'].pk}&classe={m['classe'].pk}&enseignement={m['ens'].pk}&periode={m['trim'].pk}"),
    'emploi_du_temps_classe': lambda m: reverse('viescolaire:emploi_du_temps_pdf', args=[m['classe'].pk]),
    'emploi_du_temps_prof': lambda m: reverse('viescolaire:emploi_du_temps_prof_pdf', args=[m['prof'].pk]),
    'autorisation_conge': lambda m: reverse('personnel:conge_autorisation', args=[m['conge'].pk]),
    'contrat_travail': lambda m: reverse('personnel:contrat', args=[m['prof'].pk]) + '?format=pdf',
    'attestation_travail': lambda m: reverse('personnel:attestation_travail', args=[m['prof'].pk]) + '?format=pdf',
    'bulletin_salaire': lambda m: reverse('personnel:salaire_detail', args=[m['salaire'].pk]) + '?format=pdf',
    'livre_paie': lambda m: reverse('personnel:livre_paie_pdf') + f"?mois=10&annee={m['salaire'].annee}",
    'bulletins_salaire_lot': lambda m: reverse('personnel:bulletins_paie_lot_pdf') + f"?mois=10&annee={m['salaire'].annee}",
    'bulletin_vacation': lambda m: reverse('vacations:bulletin_vacation_pdf', args=[m['vacation'].pk]),
    'pv_conseil': lambda m: reverse('viescolaire:conseil_pv_pdf', args=[m['conseil'].pk]),
    'dossier_transfert': lambda m: reverse('inscriptions:transfert_inter_dossier_pdf', args=[m['transfert'].pk]),
    'bulletin_competences': lambda m: reverse('pedagogie:competences_bulletin_pdf', args=[m['insc'].pk, m['trim'].pk]),
    'liste_eleves': lambda m: reverse('inscriptions:eleve_list_pdf'),
    'liste_candidats': lambda m: reverse('examens:candidats_session_pdf', args=[m['session'].pk]),
    'statistiques_session': lambda m: reverse('examens:session_statistiques', args=[m['session'].pk]) + '?format=pdf',
    'statistiques_enseignants': lambda m: reverse('core:pilotage_enseignants') + '?format=pdf',
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
    reponse = url(client, monde) if callable(url) else client.get(url)
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf', url
    assert rendus, url
    textes, images = zip(*(_texte_et_images(document) for document in rendus))
    return ' '.join(textes), [classe for liste in images for classe in liste]


@pytest.mark.parametrize('document', sorted(DOCUMENTS))
def test_le_signataire_configure_est_imprime(client, monkeypatch, monde, document):
    source = DOCUMENTS[document]
    texte, images = _rendre(client, monkeypatch, monde, source if source.__name__.startswith('_post') else source(monde))
    assert 'KABORE ISSOUF' in texte.upper(), document  # certains gabarits capitalisent le nom (text-transform)
    assert 'msig-img' in images, document


def test_type_de_document_desactive_le_document_reste_signe_par_le_signataire_du_cycle(client, monkeypatch, monde):
    """« Liste du Personnel » désactivé ou supprimé dans Paramètres → Types de documents : la liste alphabétique
    du personnel du cycle imprimait un blanc, bien que le directeur du cycle soit configuré."""
    TypeDocument.objects.filter(code='LISTE_PERSONNEL').update(actif=False)
    url = reverse('documents:liste_personnel_pdf', args=[monde['classe'].cycle_id]) + '?format=pdf'
    texte, images = _rendre(client, monkeypatch, monde, url)
    assert 'Le Directeur' in texte and 'KABORE Issouf' in texte and 'msig-img' in images

    TypeDocument.objects.filter(code='LISTE_PERSONNEL').delete()
    texte, images = _rendre(client, monkeypatch, monde, url)
    assert 'KABORE Issouf' in texte and 'msig-img' in images


def test_fiche_de_discipline_signature_scannee_de_l_enseignant(client, monkeypatch, monde):
    """La fiche de discipline est certifiée par l'enseignant : c'est sa signature scannée qui s'imprime."""
    m = monde
    url = (reverse('pedagogie:fiche_discipline_pdf')
           + f"?annee={m['annee'].pk}&classe={m['classe'].pk}&enseignement={m['ens'].pk}&periode={m['trim'].pk}")
    texte, images = _rendre(client, monkeypatch, monde, url)
    assert 'ZONGO ALI' in texte and 'KABORE' not in texte  # nom en capitales (text-transform du gabarit)
    assert 'msig-img' in images
