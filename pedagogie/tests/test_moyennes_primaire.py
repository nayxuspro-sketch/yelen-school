"""Moyennes du primaire : la note saisie est la moyenne de la discipline, exprimée sur 10 (5.60.0).

Au préscolaire et au primaire, toutes les moyennes (discipline et générale) sont sur **10** et la note saisie
vaut moyenne : pas de pondération par type d'évaluation. Le bouton « Calculer les moyennes » calcule la moyenne
de chaque élève et annonce son résultat (ou l'absence de notes à moyenner).
"""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Evaluation, MoyenneGenerale, Resultat
from pedagogie.utils import CalculateurMoyenne

pytestmark = pytest.mark.django_db


@pytest.fixture
def primaire(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    prim = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire', ordre=2)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=prim, nom='CP1', niveau='CP1')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1,
                           date_debut=date(2026, 10, 1), date_fin=date(2026, 12, 31))
    math = baker.make('pedagogie.Matiere', nom='Mathématiques')
    francais = baker.make('pedagogie.Matiere', nom='Français')
    maths = baker.make('pedagogie.Enseignement', classe=classe, matiere=math, annee_scolaire=annee, est_actif=True)
    fr = baker.make('pedagogie.Enseignement', classe=classe, matiere=francais, annee_scolaire=annee, est_actif=True)
    type_eval = baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1'), nb_meilleures_notes=0)
    eleves = {}
    for nom in ('OUEDRAOGO', 'SAWADOGO', 'TRAORE'):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Awa')
        eleves[nom] = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'classe': classe, 'annee': annee, 'trimestre': trimestre, 'maths': maths,
            'francais': fr, 'type': type_eval, 'eleves': eleves, 'client': client}


def _evaluation(contexte, enseignement, bareme, titre='Moyenne du trimestre'):
    return baker.make('pedagogie.Evaluation', enseignement=enseignement, trimestre=contexte['trimestre'],
                      type_evaluation=contexte['type'], titre=titre, bareme=Decimal(bareme),
                      statut=Evaluation.StatutChoices.TERMINEE, date_planifiee=date(2026, 11, 4))


def _noter(contexte, evaluation, notes):
    for nom, valeur in notes.items():
        baker.make('pedagogie.Note', inscription=contexte['eleves'][nom], evaluation=evaluation,
                   valeur=Decimal(valeur))


def _bouton(contexte):
    return contexte['client'].post(
        reverse('pedagogie:calculer_moyennes_classe', kwargs={'class_id': contexte['classe'].pk}),
        {'trimestre_id': contexte['trimestre'].pk, 'annee_id': contexte['annee'].pk}, follow=True)


def test_la_classe_primaire_a_un_bareme_de_10(primaire):
    assert primaire['classe'].bareme_moyenne == Decimal('10')
    assert primaire['classe'].seuil_moyenne == Decimal('5')
    secondaire = baker.make('parametres.Classe', cycle=baker.make('parametres.Cycle', code='SEC'))
    assert secondaire.bareme_moyenne == Decimal('20') and secondaire.seuil_moyenne == Decimal('10')


def test_la_note_saisie_est_la_moyenne_de_la_discipline(primaire):
    """Une note sur 10 reste telle quelle : 8 → 8,00/10, sans conversion sur 20."""
    _noter(primaire, _evaluation(primaire, primaire['maths'], '10'),
           {'OUEDRAOGO': '8', 'SAWADOGO': '6.5', 'TRAORE': '4'})
    _bouton(primaire)
    resultat = Resultat.objects.get(inscription=primaire['eleves']['OUEDRAOGO'], enseignement=primaire['maths'])
    assert resultat.moyenne == Decimal('8.00')            # note = moyenne
    assert resultat.moyenne_sur_20 == Decimal('16.00')    # équivalent, pour les états secondaires
    assert (resultat.meilleure_note, resultat.pire_note) == (Decimal('8.00'), Decimal('8.00'))


def test_une_note_sur_20_est_ramenee_sur_10(primaire):
    _noter(primaire, _evaluation(primaire, primaire['maths'], '20'), {'OUEDRAOGO': '16'})
    _bouton(primaire)
    assert Resultat.objects.get(inscription=primaire['eleves']['OUEDRAOGO']).moyenne == Decimal('8.00')


def test_moyenne_generale_sur_10_rangs_et_matieres_validees(primaire):
    """Deux disciplines sur 10 → moyenne générale sur 10 ; le seuil de validation est 5/10."""
    _noter(primaire, _evaluation(primaire, primaire['maths'], '10'),
           {'OUEDRAOGO': '8', 'SAWADOGO': '6', 'TRAORE': '4'})
    _noter(primaire, _evaluation(primaire, primaire['francais'], '10', titre='Dictée'),
           {'OUEDRAOGO': '6', 'SAWADOGO': '8', 'TRAORE': '6'})
    _bouton(primaire)
    ouédraogo = MoyenneGenerale.objects.get(inscription=primaire['eleves']['OUEDRAOGO'])
    assert ouédraogo.moyenne == Decimal('7.00')
    assert ouédraogo.bareme == Decimal('10') and ouédraogo.total_points_max == Decimal('20.00')
    assert ouédraogo.moyenne_suffisante is True and ouédraogo.nb_matieres_validees == 2
    assert MoyenneGenerale.objects.get(inscription=primaire['eleves']['SAWADOGO']).moyenne == Decimal('7.00')
    traore = MoyenneGenerale.objects.get(inscription=primaire['eleves']['TRAORE'])
    assert (traore.moyenne, traore.rang) == (Decimal('5.00'), 3), 'ex aequo 7,00 → rangs 1, 1 puis 3'
    assert traore.nb_matieres_validees == 1, 'seuil 5/10 : maths 4 non validée, français 6 validée'
    assert ouédraogo.rang == 1, 'ex aequo à 7,00 → même rang'


def test_le_secondaire_reste_sur_20(primaire):
    """Aucune régression au post-primaire / secondaire : pondération par type et barème 20."""
    sec = baker.make('parametres.Cycle', etablissement=primaire['etab'], code='SEC', nom='Secondaire', ordre=4)
    classe = baker.make('parametres.Classe', etablissement=primaire['etab'], cycle=sec, nom='6ème A', niveau='6ème')
    enseignement = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=primaire['annee'],
                              matiere=baker.make('pedagogie.Matiere', nom='Histoire'), est_actif=True)
    evaluation = baker.make('pedagogie.Evaluation', enseignement=enseignement, trimestre=primaire['trimestre'],
                            type_evaluation=primaire['type'], titre='Composition', bareme=Decimal('20'),
                            statut='TERMINEE', date_planifiee=date(2026, 11, 4))
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=primaire['annee'])
    baker.make('pedagogie.Note', inscription=inscription, evaluation=evaluation, valeur=Decimal('15'))
    assert CalculateurMoyenne.calculer_resultat_matiere(
        inscription, enseignement, primaire['trimestre']).moyenne == Decimal('15.00')


def test_le_bouton_annonce_les_moyennes_calculees(primaire):
    _noter(primaire, _evaluation(primaire, primaire['maths'], '10'),
           {'OUEDRAOGO': '9', 'SAWADOGO': '7', 'TRAORE': '5'})
    page = _bouton(primaire)
    assert MoyenneGenerale.objects.count() == 3, 'la moyenne de chaque élève est calculée'
    messages = [str(m) for m in page.context['messages']]
    assert any('3 moyenne(s) calculée(s) sur 10 pour 3 élève(s)' in m for m in messages), messages


def test_le_bouton_explique_quand_il_n_y_a_rien_a_calculer(primaire):
    """Sans note sur la période, plus de « calcul terminé » trompeur : l'écran dit ce qui manque."""
    page = _bouton(primaire)
    assert not MoyenneGenerale.objects.exists()
    messages = [str(m) for m in page.context['messages']]
    assert any('Aucune moyenne calculée pour CP1' in m and 'aucune note' in m for m in messages), messages


def test_une_evaluation_notee_compte_meme_planifiee_et_l_annulee_est_ecartee(primaire):
    planifiee = _evaluation(primaire, primaire['maths'], '10')
    planifiee.statut = Evaluation.StatutChoices.PLANIFIEE
    planifiee.save(update_fields=['statut'])
    _noter(primaire, planifiee, {'OUEDRAOGO': '7'})
    annulee = _evaluation(primaire, primaire['maths'], '10', titre='Devoir annulé')
    annulee.statut = Evaluation.StatutChoices.ANNULEE
    annulee.save(update_fields=['statut'])
    _noter(primaire, annulee, {'OUEDRAOGO': '1'})       # ne doit pas tirer la moyenne vers le bas
    _bouton(primaire)
    resultat = Resultat.objects.get(inscription=primaire['eleves']['OUEDRAOGO'])
    assert resultat.moyenne == Decimal('7.00') and resultat.nb_notes == 1


def test_la_page_des_resultats_affiche_le_bareme_de_la_classe(primaire):
    _noter(primaire, _evaluation(primaire, primaire['maths'], '10'), {'OUEDRAOGO': '8'})
    _bouton(primaire)
    page = primaire['client'].get(reverse('pedagogie:resultat_classe', kwargs={'class_id': primaire['classe'].pk}),
                                  {'trimestre': primaire['trimestre'].pk, 'annee': primaire['annee'].pk})
    html = page.content.decode()
    assert '8,00' in html and '/10' in html and '/20' not in html
    assert 'À calculer' in html, 'les élèves sans note restent signalés'

def test_le_bulletin_primaire_s_affiche_sur_10_sans_note_ponderee(primaire, mocker):
    """Bulletin du primaire : « Moy. /10 », moyenne générale « 7,86 / 10 », et plus de colonne « Note pond. »."""
    _noter(primaire, _evaluation(primaire, primaire['maths'], '10'),
           {'OUEDRAOGO': '8', 'SAWADOGO': '6', 'TRAORE': '4'})
    _noter(primaire, _evaluation(primaire, primaire['francais'], '10', titre='Dictée'),
           {'OUEDRAOGO': '7,86'.replace(',', '.'), 'SAWADOGO': '8', 'TRAORE': '6'})
    _bouton(primaire)
    weasy = mocker.patch('pedagogie.views.bulletins.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    reponse = primaire['client'].get(reverse('pedagogie:bulletin_pdf', kwargs={
        'inscription_id': primaire['eleves']['OUEDRAOGO'].pk, 'trimestre_id': primaire['trimestre'].pk}))
    assert reponse.status_code == 200
    html = weasy.call_args.kwargs['string']
    assert 'Moy. /10' in html and 'Moy. /20' not in html
    assert '7,93&nbsp;/&nbsp;10' in html, 'moyenne générale (8,00 + 7,86) / 2 sur 10'
    assert 'Note pond.' not in html and 'Note pondérée' not in html, 'colonne supprimée'
    assert 'Total : 15,86&nbsp;/&nbsp;20 pts' in html, 'points obtenus / maximum (2 coef. × 10)'

    apercu = primaire['client'].get(reverse('pedagogie:bulletin_apercu', kwargs={
        'inscription_id': primaire['eleves']['OUEDRAOGO'].pk, 'trimestre_id': primaire['trimestre'].pk}))
    ecran = apercu.content.decode()
    assert 'Moy. / 10' in ecran and 'Moy. / 20' not in ecran and 'Note pond.' not in ecran
    assert '7,93 / 10' in ecran
