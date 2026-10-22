"""Import des notes d'une classe depuis le fichier existant : reconnaissance des matières et des élèves, assistant."""
import io
from datetime import date
from decimal import Decimal

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery import baker

from pedagogie import importation
from pedagogie.models import Evaluation, Note

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement', code='ETAB001')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026', est_courante=True,
                       date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, ordre=1)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6ème A', niveau='6ème')
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='1er trimestre', numero=1,
                           date_debut=date(2025, 10, 1), date_fin=date(2025, 12, 20))
    devoir = baker.make('pedagogie.TypeEvaluation', code='DEV', nom='Devoir', ordre=1)
    matieres = {
        'MATH': baker.make('pedagogie.Matiere', code='MATH', nom='Mathématiques'),
        'FR': baker.make('pedagogie.Matiere', code='FR', nom='Français'),
        'SVT': baker.make('pedagogie.Matiere', code='SVT', nom='SVT', nom_complet='Sciences de la vie et de la terre'),
        'HG': baker.make('pedagogie.Matiere', code='HG', nom='Histoire-Géographie'),
    }
    ens = {code: baker.make('pedagogie.Enseignement', matiere=m, classe=classe, annee_scolaire=annee, est_actif=True)
           for code, m in matieres.items()}
    eleves = {
        'kader': baker.make('inscriptions.Eleve', matricule='ETAB001-25-01', nom='OUEDRAOGO', prenom='Abdoul Kader',
                            genre='M', date_naissance=date(2012, 5, 12)),
        'awa': baker.make('inscriptions.Eleve', matricule='ETAB001-25-02', nom='SAWADOGO', prenom='Awa Marie',
                          genre='F', date_naissance=date(2011, 9, 3)),
        'fati': baker.make('inscriptions.Eleve', matricule='ETAB001-25-03', nom='ZONGO', prenom='Fati',
                           genre='F', date_naissance=date(2012, 1, 1)),
    }
    inscriptions = {cle: baker.make('inscriptions.Inscription', eleve=e, classe=classe, annee_scolaire=annee,
                                    statut='ACTIF') for cle, e in eleves.items()}
    return {'etab': etab, 'annee': annee, 'classe': classe, 'trimestre': trimestre, 'devoir': devoir,
            'ens': ens, 'inscriptions': inscriptions}


@pytest.fixture
def secretaire(client, ecole):
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='SECRETAIRE',
                                  email='secretariat@ecole.bf', must_change_password=False))
    return client


def _xlsx(lignes):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'T1'
    ws.append(['NOTES DU 1er TRIMESTRE — 6ème A'])
    for ligne in lignes:
        ws.append(ligne)
    tampon = io.BytesIO()
    wb.save(tampon)
    return SimpleUploadedFile('notes_6eA_T1.xlsx', tampon.getvalue())


LIGNES_NOTES = [
    ['N°', 'Nom et Prénoms', 'Math', 'Français', 'Sciences de la vie et de la terre', 'HG', 'Moyenne', 'Rang'],
    [1, 'OUEDRAOGO Abdoul Kader', 12.5, '14,25', 'ABS', 9, 11.9, 2],
    [2, 'SAWADOGO Awa Marie', 17, 15, 16, 18.5, 16.6, 1],
    [3, 'ZONGO Fati', 25, None, 8, 'absente', 8, 3],            # 25 > barème ; « absente » = ABS
    [4, 'KABORE Issa', 10, 10, 10, 10, 10, 4],                   # pas inscrit dans la classe
]


def _parametres(ecole, **extra):
    return {'classe': ecole['classe'].pk, 'trimestre': ecole['trimestre'].pk, 'type_evaluation': ecole['devoir'].pk,
            'titre': 'Devoir 1', 'bareme': '20', 'date_evaluation': '2025-11-15', **extra}


def _jusqu_a_la_verification(client, ecole, fichier):
    reponse = client.post(reverse('pedagogie:notes_import'), _parametres(ecole, fichier=fichier))
    assert reponse.status_code == 302 and reponse.url == reverse('pedagogie:notes_import_correspondance')
    page = client.get(reverse('pedagogie:notes_import_correspondance'))
    assert page.status_code == 200
    donnees = {'feuille': page.context['feuille'].nom}
    for ligne in page.context['champs']:
        donnees[f'col_{ligne["champ"].code}'] = '' if ligne['index'] is None else str(ligne['index'])
    for colonne in page.context['colonnes']:
        if colonne['enseignement'] is not None:
            donnees[f'mat_{colonne["index"]}'] = str(colonne['enseignement'].pk)
    return page, donnees


def test_detection_des_matieres_par_nom_debut_commun_et_initiales(ecole):
    entetes = ['N°', 'Nom et Prénoms', 'Math', 'Français', 'Sciences de la vie et de la terre', 'HG', 'Moyenne', 'Rang']
    corr = importation.detecter_matieres(entetes, list(ecole['ens'].values()), {1})
    assert {i: e.matiere.code for i, e in corr.items()} == {2: 'MATH', 3: 'FR', 4: 'SVT', 5: 'HG'}
    assert importation.verifier_correspondance({'nom_complet': 1}, corr) == []
    assert importation.verifier_correspondance({'nom': 1}, {}) != []


def test_import_complet_puis_reimport_met_a_jour(secretaire, ecole):
    page, donnees = _jusqu_a_la_verification(secretaire, ecole, _xlsx(LIGNES_NOTES))
    assert page.context['nb_matieres'] == 4 and donnees['col_nom_complet'] == '1'
    assert secretaire.post(reverse('pedagogie:notes_import_correspondance'), donnees).status_code == 302

    verification = secretaire.get(reverse('pedagogie:notes_import_verification'))
    analyse = verification.context['analyse']
    assert analyse.nb_eleves == 3 and analyse.nb_notes == 10 and analyse.nb_remplacees == 0 and not analyse.bloquants
    assert sorted(motif for _, _, motif in analyse.erreurs) == [
        'Mathématiques : note 25 hors barème (0 à 20)', 'élève introuvable parmi les inscrits de la classe',
    ]
    assert Note.objects.count() == 0
    contenu = verification.content.decode()
    assert 'Importer 10 notes pour 3 élèves' in contenu and 'Histoire-Géographie' in contenu

    reponse = secretaire.post(reverse('pedagogie:notes_import_verification'))
    assert reponse.status_code == 302 and reponse.url == reverse('pedagogie:notes_import_resultat')
    resultat = secretaire.get(reverse('pedagogie:notes_import_resultat')).context['resultat']
    assert resultat == {'evaluations_creees': 4, 'notes_creees': 10, 'notes_remplacees': 0, 'nb_eleves': 3,
                        'nb_matieres': 4, 'nb_erreurs': 2}
    evaluation = Evaluation.objects.get(enseignement=ecole['ens']['FR'])
    assert evaluation.titre == 'Devoir 1' and evaluation.bareme == 20 and evaluation.date_planifiee == date(2025, 11, 15)
    kader = ecole['inscriptions']['kader']
    assert Note.objects.get(inscription=kader, evaluation=evaluation).valeur == Decimal('14.25')
    svt = Note.objects.get(inscription=kader, evaluation__enseignement=ecole['ens']['SVT'])
    assert svt.valeur == 0 and svt.observation == 'ABS'
    assert Note.objects.filter(inscription=ecole['inscriptions']['fati']).count() == 2   # SVT et HG (ABS)

    # Fichier corrigé réimporté : notes mises à jour, aucune évaluation ni note dupliquée.
    corrige = [LIGNES_NOTES[0], LIGNES_NOTES[1], LIGNES_NOTES[2], [3, 'ZONGO Fati', 15, 11, 8, 'ABS', 8, 3]]
    _, donnees = _jusqu_a_la_verification(secretaire, ecole, _xlsx(corrige))
    secretaire.post(reverse('pedagogie:notes_import_correspondance'), donnees)
    assert secretaire.get(reverse('pedagogie:notes_import_verification')).context['analyse'].nb_remplacees == 10
    secretaire.post(reverse('pedagogie:notes_import_verification'))
    resultat = secretaire.get(reverse('pedagogie:notes_import_resultat')).context['resultat']
    assert resultat['evaluations_creees'] == 0 and resultat['notes_creees'] == 2 and resultat['notes_remplacees'] == 10
    assert Evaluation.objects.count() == 4 and Note.objects.count() == 12
    fati_math = Note.objects.get(inscription=ecole['inscriptions']['fati'], evaluation__enseignement=ecole['ens']['MATH'])
    assert fati_math.valeur == 15 and fati_math.observation == ''
    rapport = secretaire.get(reverse('pedagogie:notes_import_rapport'))
    assert rapport.status_code == 200 and rapport['Content-Type'].endswith('sheet')


def test_reconnaissance_par_matricule_et_homonymes(secretaire, ecole):
    jumeau = baker.make('inscriptions.Eleve', matricule='ETAB001-25-04', nom='ZONGO', prenom='Fati', genre='F',
                        date_naissance=date(2012, 1, 1))
    baker.make('inscriptions.Inscription', eleve=jumeau, classe=ecole['classe'], annee_scolaire=ecole['annee'])
    csv = ('Matricule;Nom;Prénom;MATH\n'
           'ETAB001-25-01;OUEDRAOGO;Abdoul Kader;12\n'
           ';ZONGO;Fati;14\n'                 # homonymes sans matricule → ambigu
           'ETAB001-25-04;ZONGO;Fati;16\n').encode('utf-8')
    _, donnees = _jusqu_a_la_verification(secretaire, ecole, SimpleUploadedFile('notes.csv', csv))
    assert donnees['col_matricule'] == '0' and donnees['mat_3'] == str(ecole['ens']['MATH'].pk)
    secretaire.post(reverse('pedagogie:notes_import_correspondance'), donnees)
    analyse = secretaire.get(reverse('pedagogie:notes_import_verification')).context['analyse']
    assert analyse.nb_eleves == 2 and analyse.nb_notes == 2
    assert [m for _, _, m in analyse.erreurs] == ['homonymes dans la classe : ajoutez la colonne Matricule']


def test_bareme_different_d_une_evaluation_existante_bloque(secretaire, ecole):
    baker.make('pedagogie.Evaluation', enseignement=ecole['ens']['MATH'], trimestre=ecole['trimestre'],
               type_evaluation=ecole['devoir'], titre='Devoir 1', bareme=10, date_planifiee=date(2025, 11, 1))
    _, donnees = _jusqu_a_la_verification(secretaire, ecole, _xlsx(LIGNES_NOTES[:3]))
    secretaire.post(reverse('pedagogie:notes_import_correspondance'), donnees)
    verification = secretaire.get(reverse('pedagogie:notes_import_verification'))
    assert verification.context['analyse'].bloquants == [
        'Une évaluation « Devoir 1 » existe déjà en Mathématiques pour ce trimestre avec un barème de 10 : '
        'reprenez ce barème ou changez le titre.']
    secretaire.post(reverse('pedagogie:notes_import_verification'))
    assert Note.objects.count() == 0


def test_parametres_invalides_et_classe_sans_enseignement(secretaire, ecole):
    vide = baker.make('parametres.Classe', etablissement=ecole['etab'], cycle=ecole['classe'].cycle, nom='5ème B')
    reponse = secretaire.post(reverse('pedagogie:notes_import'),
                              _parametres(ecole, fichier=_xlsx(LIGNES_NOTES[:2]), classe=vide.pk), follow=True)
    assert "Aucun enseignement n'est défini pour la classe 5ème B" in reponse.content.decode().replace('&#x27;', "'")
    reponse = secretaire.post(reverse('pedagogie:notes_import'),
                              _parametres(ecole, fichier=_xlsx(LIGNES_NOTES[:2]), bareme='abc'), follow=True)
    assert 'Barème invalide' in reponse.content.decode()
    assert secretaire.get(reverse('pedagogie:notes_import_verification')).url == reverse('pedagogie:notes_import')


def test_enseignant_refuse_et_bouton_reserve(client, secretaire, ecole):
    assert 'Importer des notes' in secretaire.get(reverse('pedagogie:evaluation_list')).content.decode()
    client.logout()
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='ENSEIGNANT',
                                  email='prof@ecole.bf', must_change_password=False))
    assert client.get(reverse('pedagogie:notes_import')).status_code == 302
    assert 'Importer des notes' not in client.get(reverse('pedagogie:evaluation_list')).content.decode()
