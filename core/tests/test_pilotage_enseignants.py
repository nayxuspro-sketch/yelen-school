"""Lot H — statistiques par enseignant : charge (classes, élèves, heures), évaluations, taux de saisie des notes,
moyenne et réussite des élèves, cahier de textes, appréciations ; filtre par période ; écran, PDF et droits."""
from datetime import date, time
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.statistiques_enseignants import statistiques_enseignants

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    t1 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1,
                    date_debut=date(2026, 10, 1), date_fin=date(2026, 12, 20))
    t2 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 2', numero=2,
                    date_debut=date(2027, 1, 5), date_fin=date(2027, 3, 31))
    c6 = baker.make('parametres.Classe', etablissement=etab, nom='6e A', actif=True)
    c5 = baker.make('parametres.Classe', etablissement=etab, nom='5e A', actif=True)
    maths = baker.make('pedagogie.Matiere', code='MATH', nom='Mathématiques')
    pc = baker.make('pedagogie.Matiere', code='PC', nom='Physique-Chimie')
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Ali', fonction='Professeur')
    ens6 = baker.make('pedagogie.Enseignement', classe=c6, matiere=maths, personnel=prof, annee_scolaire=annee, est_actif=True)
    ens5 = baker.make('pedagogie.Enseignement', classe=c5, matiere=pc, personnel=prof, annee_scolaire=annee, est_actif=True)
    libre = baker.make('pedagogie.Enseignement', classe=c5, matiere=maths, personnel=None, annee_scolaire=annee, est_actif=True)
    baker.make('pedagogie.Enseignement', classe=c6, matiere=pc, personnel=prof, annee_scolaire=annee, est_actif=False)

    def inscrire(classe, n, statut='AFFECTE'):
        return [baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut=statut,
                           eleve=baker.make('inscriptions.Eleve', date_naissance=date(2013, 1, 1), photo=''))
                for _ in range(n)]

    e6 = inscrire(c6, 3)
    inscrire(c6, 1, statut='ABANDON')
    e5 = inscrire(c5, 2)
    baker.make('viescolaire.SeanceCours', enseignement=ens6, jour=1, heure_debut=time(8, 0), heure_fin=time(10, 0))
    baker.make('viescolaire.SeanceCours', enseignement=ens6, jour=3, heure_debut=time(8, 0), heure_fin=time(9, 30))
    baker.make('viescolaire.SeanceCours', enseignement=ens5, jour=2, heure_debut=time(10, 0), heure_fin=time(11, 0))
    type_ev = baker.make('pedagogie.TypeEvaluation', code='DEV', nom='Devoir')
    ev1 = baker.make('pedagogie.Evaluation', enseignement=ens6, trimestre=t1, type_evaluation=type_ev, statut='TERMINEE',
                     date_planifiee=date(2026, 11, 2))
    ev2 = baker.make('pedagogie.Evaluation', enseignement=ens6, trimestre=t1, type_evaluation=type_ev, statut='PLANIFIEE',
                     date_planifiee=date(2026, 12, 1))
    baker.make('pedagogie.Evaluation', enseignement=ens6, trimestre=t1, type_evaluation=type_ev, statut='ANNULEE',
               date_planifiee=date(2026, 12, 2))
    baker.make('pedagogie.Evaluation', enseignement=ens5, trimestre=t2, type_evaluation=type_ev, statut='TERMINEE',
               date_planifiee=date(2027, 2, 1))
    for ins in e6:
        baker.make('pedagogie.Note', inscription=ins, evaluation=ev1, valeur=Decimal('12'))
    baker.make('pedagogie.Note', inscription=e6[0], evaluation=ev2, valeur=Decimal('15'))
    baker.make('pedagogie.Resultat', inscription=e6[0], enseignement=ens6, trimestre=t1, moyenne=Decimal('14.00'), appreciation='Bien')
    baker.make('pedagogie.Resultat', inscription=e6[1], enseignement=ens6, trimestre=t1, moyenne=Decimal('8.00'), appreciation='')
    baker.make('pedagogie.Resultat', inscription=e6[2], enseignement=ens6, trimestre=t1, moyenne=None, dispense=True, appreciation='Dispensé')
    baker.make('pedagogie.Resultat', inscription=e5[0], enseignement=ens5, trimestre=t2, moyenne=Decimal('11.00'), appreciation='Peut mieux faire')
    baker.make('pedagogie.CahierTextes', enseignement=ens6, date=date(2026, 11, 3), contenu='Fractions')
    baker.make('pedagogie.CahierTextes', enseignement=ens6, date=date(2027, 1, 10), contenu='Décimaux')
    baker.make('pedagogie.CahierTextes', enseignement=libre, date=date(2026, 11, 3), contenu='Sans prof')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'annee': annee, 't1': t1, 't2': t2, 'prof': prof, 'user': user}


def test_charge_evaluations_saisie_resultats_sur_l_annee(ecole):
    e = ecole
    lignes = statistiques_enseignants(e['etab'], e['annee'])
    assert [l['nom'] for l in lignes] == ['ZONGO Ali', 'Non attribué'], 'enseignement inactif ignoré, sans prof en dernier'
    ali = lignes[0]
    assert (ali['fonction'], ali['nb_classes'], ali['eleves'], ali['libelle_classes']) == ('Professeur', 2, 5, '5e A, 6e A')
    assert ali['libelle_disciplines'] == 'Mathématiques, Physique-Chimie' and ali['heures'] == 4.5
    assert (ali['evaluations'], ali['evaluations_terminees']) == (3, 2), 'annulée exclue'
    assert (ali['notes_saisies'], ali['notes_attendues'], ali['taux_saisie']) == (4, 8, 50.0), '2 évals × 3 élèves + 1 × 2'
    assert (ali['resultats'], ali['moyenne'], ali['taux_reussite']) == (3, Decimal('11.00'), 66.7), 'dispensé exclu'
    assert (ali['cahier'], ali['appreciations']) == (2, 3)

    d5, d6 = ali['details']                                   # ordre : nom de classe
    assert (d6['classe'], d6['matiere'], d6['effectif'], d6['heures']) == ('6e A', 'Mathématiques', 3, 3.5)
    assert (d6['evaluations'], d6['notes_saisies'], d6['notes_attendues'], d6['taux_saisie']) == (2, 4, 6, 66.7)
    assert (d6['resultats'], d6['moyenne'], d6['taux_reussite'], d6['cahier'], d6['appreciations']) == (2, Decimal('11.00'), 50.0, 2, 2)
    assert (d5['classe'], d5['effectif'], d5['heures'], d5['evaluations'], d5['taux_saisie']) == ('5e A', 2, 1.0, 1, 0.0)
    assert (d5['moyenne'], d5['taux_reussite']) == (Decimal('11.00'), 100.0)

    libre = lignes[1]
    assert (libre['personnel'], libre['libelle_classes'], libre['heures'], libre['cahier'], libre['moyenne']) == (None, '5e A', 0.0, 1, None)


def test_filtre_par_periode(ecole):
    e = ecole
    t1 = statistiques_enseignants(e['etab'], e['annee'], e['t1'])[0]
    assert (t1['evaluations'], t1['notes_saisies'], t1['notes_attendues'], t1['resultats'], t1['cahier']) == (2, 4, 6, 2, 1)
    assert t1['heures'] == 4.5, "la charge hebdomadaire ne dépend pas de la période"
    t2 = statistiques_enseignants(e['etab'], e['annee'], e['t2'])[0]
    assert (t2['evaluations'], t2['notes_saisies'], t2['resultats'], t2['moyenne'], t2['cahier'], t2['appreciations']) \
        == (1, 0, 1, Decimal('11.00'), 1, 1)


def test_sans_enseignement(ecole):
    assert statistiques_enseignants(baker.make('etablissements.Etablissement'), ecole['annee']) == []


def test_ecran_pdf_et_droits(client, ecole, mocker):
    e = ecole
    url = reverse('core:pilotage_enseignants')
    page = client.get(url)
    assert page.status_code == 200 and [l['nom'] for l in page.context['lignes']] == ['ZONGO Ali', 'Non attribué']
    html = page.content.decode()
    assert 'ZONGO Ali' in html and 'Non attribué' in html and '5e A, 6e A' in html

    page = client.get(url + f'?trimestre={e["t2"].pk}')
    assert page.context['trimestre'] == e['t2'] and page.context['lignes'][0]['evaluations'] == 1
    assert client.get(url + '?trimestre=inconnu').context['trimestre'] is None

    weasy = mocker.patch('core.pdf.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-ens'
    pdf = client.get(url + '?format=pdf')
    assert pdf.status_code == 200 and pdf.content == b'%PDF-ens'
    source = weasy.call_args.kwargs['string']
    assert 'Statistiques par enseignant' in source and 'ZONGO Ali' in source and 'Non attribué' in source

    lien = client.get(reverse('core:pilotage')).content.decode()
    assert url in lien

    client.force_login(baker.make('accounts.User', etablissement=e['etab'], role='SECRETAIRE', must_change_password=False))
    refus = client.get(url)
    assert refus.status_code == 200 and 'réservées à la direction' in refus.content.decode()
    assert 'lignes' not in refus.context
