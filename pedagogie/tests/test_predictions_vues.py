"""Prédictions de réussite et risque de décrochage — parcours complets (couverture 5.47.1).

Ces deux écrans engagent une décision (conseil de classe, passage, alerte d'abandon) et n'étaient couverts
qu'à 25 %. Les tests suivent les gestes réels : ouvrir la liste, filtrer, recalculer un élève,
recalculer tout, refuser un identifiant inconnu, lire le tableau de bord puis le PDF.
"""
import sys
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import RisqueDecrochage

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexte(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR')
    directeur = baker.make('accounts.User', is_superuser=True, role='DIRECTEUR', etablissement=etab,
                           must_change_password=False)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    autre = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026', est_courante=False,
                       date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    autre_classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='4e B', actif=True)
    eleves = []
    for nom in ('OUEDRAOGO', 'SAWADOGO', 'ZONGO', 'KABORE'):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Awa', photo='')
        eleves.append(baker.make('inscriptions.Inscription', eleve=eleve, classe=classe,
                                 annee_scolaire=annee, statut='ACTIF'))
    abandon = baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Eric', photo='')
    baker.make('inscriptions.Inscription', eleve=abandon, classe=classe, annee_scolaire=annee, statut='ABANDON')
    client.force_login(directeur)
    return {'client': client, 'etab': etab, 'annee': annee, 'autre_annee': autre, 'classe': classe,
            'autre_classe': autre_classe, 'eleves': eleves, 'directeur': directeur, 'abandon': abandon}


# ── Risque de décrochage ─────────────────────────────────────────────────────

def test_risque_decrochage_liste_et_compte_par_niveau(contexte):
    """La liste affiche les scores calculés, compte les niveaux et laisse l'abandon hors périmètre."""
    for i, (ins, score) in enumerate(zip(contexte['eleves'], (85, 55, 25, 10))):
        baker.make('pedagogie.RisqueDecrochage', inscription=ins,
                   niveau=RisqueDecrochage.niveau_pour_score(score), score=score)
    baker.make('pedagogie.RisqueDecrochage', inscription=baker.make(
        'inscriptions.Inscription', eleve=baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Eric', photo=''),
        classe=contexte['classe'], annee_scolaire=contexte['annee'], statut='ABANDON'),
        niveau=RisqueDecrochage.niveau_pour_score(99), score=99)

    reponse = contexte['client'].get(reverse('pedagogie:risque_decrochage'))
    html = reponse.content.decode()
    assert reponse.status_code == 200
    assert 'OUEDRAOGO' in html and 'SAWADOGO' in html
    assert contexte['classe'].nom in html
    assert reponse.context['stats']['total'] == 4, "l'inscription en abandon ne compte pas"
    assert reponse.context['stats'][RisqueDecrochage.niveau_pour_score(85)] >= 1


def test_risque_decrochage_filtres_niveau_classe_et_annee(contexte):
    """Les deux filtres de la page réduisent réellement la liste affichée."""
    niveau_eleve = RisqueDecrochage.niveau_pour_score(85)
    baker.make('pedagogie.RisqueDecrochage', inscription=contexte['eleves'][0], niveau=niveau_eleve, score=85)
    baker.make('pedagogie.RisqueDecrochage', inscription=contexte['eleves'][1],
               niveau=RisqueDecrochage.niveau_pour_score(20), score=20)

    url = reverse('pedagogie:risque_decrochage')
    par_niveau = contexte['client'].get(url, {'niveau': niveau_eleve})
    assert [r.inscription for r in par_niveau.context['risques']] == [contexte['eleves'][0]]
    assert par_niveau.context['niveau_filtre'] == niveau_eleve

    par_classe = contexte['client'].get(url, {'classe': str(contexte['autre_classe'].pk)})
    assert list(par_classe.context['risques']) == []

    par_annee = contexte['client'].get(url, {'annee': str(contexte['autre_annee'].pk)})
    assert par_annee.context['annee'] == contexte['autre_annee']
    assert list(par_annee.context['risques']) == []


def test_risque_decrochage_recalcul_unitaire_et_reponse_htmx(contexte):
    """Recalcul d'un élève : la ligne est créée puis re-rendue seule (htmx), la page n'est pas rechargée."""
    url = reverse('pedagogie:risque_decrochage')
    ins = contexte['eleves'][1]
    reponse = contexte['client'].post(url, {'inscription_id': str(ins.pk)})
    assert reponse.status_code == 302
    risque = RisqueDecrochage.objects.get(inscription=ins)
    assert 0 <= risque.score <= 100 and risque.niveau

    htmx = contexte['client'].post(url, {'inscription_id': str(ins.pk)}, HTTP_HX_REQUEST='true')
    assert htmx.status_code == 200
    assert htmx['HX-Trigger'] == 'risqueUpdated'
    assert 'hx' in htmx.content.decode().lower()


def test_risque_decrochage_identifiant_inconnu_est_signale(contexte):
    """Un identifiant inconnu ne crée rien : message d'erreur en HTML, 404 en htmx."""
    url = reverse('pedagogie:risque_decrochage')
    avant = RisqueDecrochage.objects.count()
    reponse = contexte['client'].post(url, {'inscription_id': '00000000-0000-0000-0000-000000000000'})
    assert reponse.status_code == 302 and RisqueDecrochage.objects.count() == avant
    htmx = contexte['client'].post(url, {'inscription_id': '00000000-0000-0000-0000-000000000000'},
                                   HTTP_HX_REQUEST='true')
    assert htmx.status_code == 404


def test_risque_decrochage_recalculer_tout_couvre_la_classe(contexte):
    """« Recalculer tout » traite tous les élèves actifs de l'année, jamais l'abandon."""
    url = reverse('pedagogie:risque_decrochage')
    reponse = contexte['client'].post(url, {'recalculer_tout': '1'}, HTTP_HX_REQUEST='true')
    assert reponse.status_code == 200 and reponse['HX-Refresh'] == 'true'
    assert RisqueDecrochage.objects.count() == len(contexte['eleves'])
    assert not RisqueDecrochage.objects.filter(inscription__statut='ABANDON').exists()

    redirection = contexte['client'].post(url, {'recalculer_tout': '1'})
    assert redirection.status_code == 302


def test_risque_decrochage_post_sans_cible_repond_ok(contexte):
    """Un POST htmx vide (double clic, ligne déjà traitée) reste sans effet et ne casse pas la liste."""
    avant = RisqueDecrochage.objects.count()
    reponse = contexte['client'].post(reverse('pedagogie:risque_decrochage'), {'inscription_id': ''},
                                      HTTP_HX_REQUEST='true')
    assert reponse.status_code == 200 and reponse.content == b'Ok'
    assert RisqueDecrochage.objects.count() == avant


def test_risque_decrochage_fragment_de_stats(contexte):
    """Le fragment htmx des compteurs est rendu seul (pas la page entière)."""
    reponse = contexte['client'].get(reverse('pedagogie:risque_decrochage'), {'_partial': 'stats'},
                                     HTTP_HX_REQUEST='true')
    assert reponse.status_code == 200
    assert '<html' not in reponse.content.decode().lower()


def test_risque_decrochage_pdf(contexte, mocker):
    """Le PDF reprend le tableau ; si le moteur manque, la page le dit au lieu d'échouer."""
    baker.make('pedagogie.RisqueDecrochage', inscription=contexte['eleves'][0],
               niveau=RisqueDecrochage.niveau_pour_score(85), score=85)
    moteur = mocker.patch('core.pdf.HTML')
    moteur.return_value.write_pdf.return_value = b'%PDF-1.4 risque'
    reponse = contexte['client'].get(reverse('pedagogie:risque_decrochage_pdf'),
                                     {'niveau': RisqueDecrochage.niveau_pour_score(85),
                                      'classe': str(contexte['classe'].pk)})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content == b'%PDF-1.4 risque'
    assert 'OUEDRAOGO' in moteur.call_args.kwargs['string']

    mocker.patch.dict(sys.modules, {'core.pdf': None})   # moteur absent du serveur
    sans_moteur = contexte['client'].get(reverse('pedagogie:risque_decrochage_pdf'), follow=True)
    assert sans_moteur.status_code == 200
    assert 'WeasyPrint' in sans_moteur.content.decode()


# ── Prédictions de réussite ──────────────────────────────────────────────────

def test_prediction_index_ne_propose_que_les_cycles_a_examen(contexte):
    """Le sélecteur ne liste que les classes des cycles d'examen ; les autres restent hors choix."""
    primaire = baker.make('parametres.Cycle', etablissement=contexte['etab'], code='PRI', nom='Primaire')
    classe_primaire = baker.make('parametres.Classe', etablissement=contexte['etab'], cycle=primaire,
                                 nom='CM2', actif=True)
    maternelle = baker.make('parametres.Cycle', etablissement=contexte['etab'], code='MAT', nom='Maternelle')
    classe_maternelle = baker.make('parametres.Classe', etablissement=contexte['etab'], cycle=maternelle,
                                   nom='PS', actif=True)
    reponse = contexte['client'].get(reverse('pedagogie:prediction_index'))
    assert reponse.status_code == 200
    proposees = {c.nom for c in reponse.context['classes']}
    assert contexte['classe'].nom in proposees and classe_primaire.nom in proposees
    assert classe_maternelle.nom not in proposees, 'un cycle sans examen n’est pas proposé'
    assert {c.nom for c in reponse.context['toutes_classes']} > proposees


def test_prediction_classe_compte_les_pronostics(contexte):
    """Le tableau de bord d'une classe ventile les élèves par pronostic."""
    for ins, pronostic in zip(contexte['eleves'], ('BON', 'MOYEN', 'RISQUE', 'CRITIQUE')):
        baker.make('pedagogie.PredictionReussiteExamen', inscription=ins, pronostic=pronostic, score=50)
    reponse = contexte['client'].get(
        reverse('pedagogie:prediction_classe', kwargs={'class_id': contexte['classe'].pk}))
    assert reponse.status_code == 200
    contexte_html = reponse.context
    assert (contexte_html['nb_bon'], contexte_html['nb_moyen'],
            contexte_html['nb_risque'], contexte_html['nb_critique']) == (1, 1, 1, 1)
    assert contexte_html['nb_total'] == 4
    assert 'OUEDRAOGO' in reponse.content.decode()


def test_prediction_calculer_refuse_get_et_recalcule(contexte, mocker):
    """Le calcul n'accepte que POST ; il remplace les prédictions de la classe et redirige vers le tableau."""
    url = reverse('pedagogie:prediction_calculer', kwargs={'class_id': contexte['classe'].pk})
    assert contexte['client'].get(url).status_code == 405

    calcul = mocker.patch('pedagogie.predictions.calculer_predictions_classe', return_value=[1, 2, 3])
    reponse = contexte['client'].post(url)
    assert reponse.status_code == 302
    assert reponse.url == reverse('pedagogie:prediction_classe', kwargs={'class_id': contexte['classe'].pk})
    calcul.assert_called_once()


def test_prediction_classe_pdf(contexte, mocker):
    """Le rapport PDF de la classe est produit ; sans moteur, retour au tableau avec un message."""
    baker.make('pedagogie.PredictionReussiteExamen', inscription=contexte['eleves'][0], pronostic='BON', score=80)
    moteur = mocker.patch('pedagogie.views.predictions.HTML')
    moteur.return_value.write_pdf.return_value = b'%PDF-1.4 prediction'
    reponse = contexte['client'].get(
        reverse('pedagogie:prediction_classe_pdf', kwargs={'class_id': contexte['classe'].pk}))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content == b'%PDF-1.4 prediction'
    assert 'OUEDRAOGO' in moteur.call_args.kwargs['string']

    mocker.patch('pedagogie.views.predictions.HTML', None)
    sans_moteur = contexte['client'].get(
        reverse('pedagogie:prediction_classe_pdf', kwargs={'class_id': contexte['classe'].pk}), follow=True)
    assert 'WeasyPrint' in sans_moteur.content.decode()


def test_prediction_classe_inconnue_renvoie_404(contexte):
    """Une classe inexistante est un 404, pas une page vide."""
    url = reverse('pedagogie:prediction_classe',
                  kwargs={'class_id': '00000000-0000-0000-0000-000000000000'})
    assert contexte['client'].get(url).status_code == 404


def test_les_predicitions_ne_fuient_pas_d_une_classe_a_l_autre(contexte):
    """Chaque élève n'apparaît que dans le tableau de sa classe."""
    baker.make('pedagogie.PredictionReussiteExamen', inscription=contexte['eleves'][0], pronostic='BON', score=80)
    baker.make('pedagogie.PredictionReussiteExamen', inscription=contexte['eleves'][1], pronostic='BON', score=70)
    # L'élève 2 est réinscrit dans l'autre classe la même année : il ne doit pas apparaître deux fois.
    contexte['eleves'][1].classe = contexte['autre_classe']
    contexte['eleves'][1].save(update_fields=['classe'])

    ici = contexte['client'].get(reverse('pedagogie:prediction_classe',
                                         kwargs={'class_id': contexte['classe'].pk}))
    assert ici.context['nb_total'] == 1
    la_bas = contexte['client'].get(reverse('pedagogie:prediction_classe',
                                            kwargs={'class_id': contexte['autre_classe'].pk}))
    assert la_bas.context['nb_total'] == 1
