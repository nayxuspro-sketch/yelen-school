"""Tests du service de prédiction de réussite aux examens (pedagogie/predictions.py)."""
from datetime import date
from decimal import Decimal

import pytest
from model_bakery import baker

from pedagogie import predictions
from pedagogie.models import MoyenneGenerale, PredictionReussiteExamen as P, Trimestre

pytestmark = pytest.mark.django_db


@pytest.fixture
def classe():
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Post-primaire', code='POST')
    return baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', niveau='3e', actif=True), annee


def _inscrit(classe, annee, *moyennes, statut='AFFECTE'):
    ins = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut=statut,
                     eleve__date_naissance=date(2011, 1, 1))
    for numero, moyenne in enumerate(moyennes, start=1):
        trimestre, _ = Trimestre.objects.get_or_create(
            annee_scolaire=annee, numero=numero,
            defaults={'nom': f'Trimestre {numero}', 'date_debut': date(2026, 10, 1), 'date_fin': date(2027, 6, 30)})
        baker.make(MoyenneGenerale, inscription=ins, trimestre=trimestre, moyenne=Decimal(moyenne),
                   moyenne_sur_20=Decimal(moyenne))
    return ins


def _absences(ins, nb, statut='ABSENT'):
    for j in range(nb):
        appel = baker.make('presences.Appel', classe=ins.classe, annee_scolaire=ins.annee_scolaire,
                           date=date(2026, 11, 1 + j % 28))
        baker.make('presences.Presence', appel=appel, inscription=ins, statut=statut)


@pytest.mark.parametrize('cycle, examen', [
    ('Secondaire', P.ExamenChoices.BAC), ('Post-primaire', P.ExamenChoices.BEPC), ('Collège', P.ExamenChoices.BEPC),
    ('Primaire', P.ExamenChoices.CEP), ('Maternelle', P.ExamenChoices.AUTRE), (None, P.ExamenChoices.AUTRE),
])
def test_examen_pour_cycle(cycle, examen):
    assert predictions._examen_pour_cycle(cycle) == examen


def test_sans_moyenne_aucune_prediction(classe):
    ins = _inscrit(*classe)
    assert predictions.calculer_prediction(ins) is None
    assert not P.objects.exists()


def test_score_de_base_sur_la_derniere_moyenne(classe):
    pred = predictions.calculer_prediction(_inscrit(*classe, '14.00'))
    assert (pred.score, pred.pronostic, pred.examen_cible) == (70, P.PronosticChoices.BON, P.ExamenChoices.BEPC)
    assert pred.mg_actuelle == Decimal('14.00') and pred.tendance is None and pred.nb_absences_nj == 0
    assert [f['libelle'] for f in pred.facteurs] == ['Moyenne générale (Trimestre 1)']
    assert pred.facteurs[0]['detail'] == '14,00/20' and pred.facteurs[0]['points'] == 70.0


@pytest.mark.parametrize('t1, t2, bonus', [
    ('10.00', '12.00', 10), ('10.00', '10.50', 5), ('10.00', '10.20', 0),
    ('10.00', '9.00', -5), ('10.00', '7.50', -10),
])
def test_tendance_inter_trimestrielle(classe, t1, t2, bonus):
    pred = predictions.calculer_prediction(_inscrit(*classe, t1, t2))
    attendu = max(0, min(100, round(float(t2) / 20 * 100 + bonus)))
    assert pred.score == attendu
    assert pred.tendance == Decimal(t2) - Decimal(t1)
    facteur = pred.facteurs[1]
    assert facteur['libelle'] == 'Tendance inter-trimestrielle' and facteur['points'] == bonus
    assert '(Trimestre 2 vs Trimestre 1)' in facteur['detail']
    assert facteur['detail'].startswith('+') is (Decimal(t2) > Decimal(t1))


@pytest.mark.parametrize('nb_absences, malus', [(0, 0), (10, 0), (11, -5), (21, -10), (31, -15)])
def test_malus_absences_non_justifiees(classe, nb_absences, malus):
    ins = _inscrit(*classe, '12.00')
    _absences(ins, nb_absences)
    _absences(ins, 12, statut='EXCUSE')      # les absences justifiées ne pénalisent pas
    pred = predictions.calculer_prediction(ins)
    assert pred.nb_absences_nj == nb_absences and pred.score == 60 + malus
    assidu = [f for f in pred.facteurs if f['libelle'] == 'Assiduité']
    if nb_absences:
        assert assidu[0]['detail'] == f'{nb_absences} absence(s) non justifiée(s)' and assidu[0]['points'] == malus
    else:
        assert assidu == []


def test_score_borne_et_pronostics(classe):
    assert predictions.calculer_prediction(_inscrit(*classe, '17.00', '19.50')).score == 100
    assert predictions.calculer_prediction(_inscrit(*classe, '4.00', '1.00')).score == 0
    assert predictions.calculer_prediction(_inscrit(*classe, '11.00')).pronostic == P.PronosticChoices.MOYEN
    assert predictions.calculer_prediction(_inscrit(*classe, '7.00')).pronostic == P.PronosticChoices.RISQUE
    assert predictions.calculer_prediction(_inscrit(*classe, '5.00')).pronostic == P.PronosticChoices.CRITIQUE


def test_recalcul_met_a_jour_sans_doublon(classe):
    ins = _inscrit(*classe, '14.00')
    premiere = predictions.calculer_prediction(ins)
    baker.make(MoyenneGenerale, inscription=ins, moyenne=Decimal('8.00'), moyenne_sur_20=Decimal('8.00'),
               trimestre=Trimestre.objects.create(annee_scolaire=classe[1], numero=2, nom='Trimestre 2',
                                                  date_debut=date(2027, 1, 1), date_fin=date(2027, 3, 31)))
    seconde = predictions.calculer_prediction(ins)
    assert seconde.pk == premiere.pk and P.objects.count() == 1
    assert seconde.score == 30 and seconde.pronostic == P.PronosticChoices.RISQUE


def test_predictions_classe_ignore_abandons_et_sans_moyenne(classe):
    avec = _inscrit(*classe, '13.00')
    _inscrit(*classe, '15.00', statut='ABANDON')
    _inscrit(*classe)
    resultats = predictions.calculer_predictions_classe(*classe)
    assert [p.inscription_id for p in resultats] == [avec.pk]
