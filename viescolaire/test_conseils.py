"""Conseils de classe, procès-verbaux et appels de décision (couverture 5.47.1).

Le conseil de classe est l'écran où l'établissement engage une décision d'orientation :
chaque test suit un geste réel (créer, marquer tenu, saisir les décisions, imprimer le PV,
déposer puis instruire un appel) au lieu de vérifier des détails d'implémentation.
"""
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from viescolaire.models import AppelDecision, ConseilClasse, DecisionConseil
from viescolaire.views import conseils as vues_conseils

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexte(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR')
    directeur = baker.make('accounts.User', is_superuser=True, role='DIRECTEUR', etablissement=etab,
                           est_tous_cycles=True, must_change_password=False,
                           first_name='Awa', last_name='OUEDRAOGO')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2027, 6, 30))
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
                           date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2026, 12, 31))
    trimestre_2 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=2, nom='Trimestre 2',
                             date_debut=datetime.date(2027, 1, 5), date_fin=datetime.date(2027, 3, 31))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    eleves = []
    for nom, prenom in (('OUEDRAOGO', 'Awa'), ('SAWADOGO', 'Eric'), ('ZONGO', 'Fatou')):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, photo='')
        eleves.append(baker.make('inscriptions.Inscription', eleve=eleve, classe=classe,
                                 annee_scolaire=annee, statut='ACTIF'))
    absent = baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Anne', photo='')
    baker.make('inscriptions.Inscription', eleve=absent, classe=classe, annee_scolaire=annee, statut='ABANDON')
    conseil = baker.make(ConseilClasse, classe=classe, trimestre=trimestre,
                         date_conseil=datetime.date(2026, 12, 20), president=directeur, tenu=False)
    decisions = [baker.make(DecisionConseil, conseil=conseil, inscription=ins) for ins in eleves]
    client.force_login(directeur)
    return {'client': client, 'etab': etab, 'annee': annee, 'trimestre': trimestre,
            'trimestre_2': trimestre_2, 'classe': classe, 'conseil': conseil,
            'decisions': decisions, 'eleves': eleves, 'dire': directeur}


# ── Conseils de classe ───────────────────────────────────────────────────────

def test_conseil_list_montre_les_conseils_de_l_annee_courante(contexte):
    """La liste ne mélange pas les années : seuls les conseils de l'année courante s'affichent."""
    ancienne = baker.make('parametres.AnneeScolaire', etablissement=contexte['etab'], libelle='2025-2026',
                          est_courante=False, date_debut=datetime.date(2025, 10, 1),
                          date_fin=datetime.date(2026, 6, 30))
    vieux_trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=ancienne, numero=1, nom='Trimestre 1',
                                 date_debut=datetime.date(2025, 10, 1), date_fin=datetime.date(2025, 12, 31))
    ancien = baker.make(ConseilClasse, classe=contexte['classe'], trimestre=vieux_trimestre,
                        date_conseil=datetime.date(2025, 12, 20))

    reponse = contexte['client'].get(reverse('viescolaire:conseil_list'))
    assert reponse.status_code == 200
    conseils = list(reponse.context['conseils'])
    assert conseils == [contexte['conseil']] and ancien not in conseils
    assert list(reponse.context['trimestres']) == [contexte['trimestre'], contexte['trimestre_2']]

    par_trimestre = contexte['client'].get(reverse('viescolaire:conseil_list'),
                                           {'trimestre': str(contexte['trimestre_2'].pk)})
    assert list(par_trimestre.context['conseils']) == []
    assert par_trimestre.context['trimestre_selectionne'] == contexte['trimestre_2']


def test_conseil_detail_affiche_les_eleves_par_ordre_alphabetique(contexte):
    """Le détail liste les décisions triées par nom d'élève et propose les choix de décision."""
    reponse = contexte['client'].get(reverse('viescolaire:conseil_detail',
                                             kwargs={'conseil_id': contexte['conseil'].pk}))
    assert reponse.status_code == 200
    noms = [d.inscription.eleve.nom for d in reponse.context['decisions']]
    assert noms == ['OUEDRAOGO', 'SAWADOGO', 'ZONGO']
    assert reponse.context['decision_choices'] == DecisionConseil.DecisionChoices.choices


def test_conseil_marquer_tenu_puis_enregistrer_les_decisions(contexte):
    """Deux POST distincts : « tenu » puis les décisions individuelles avec mentions."""
    url = reverse('viescolaire:conseil_detail', kwargs={'conseil_id': contexte['conseil'].pk})

    reponse = contexte['client'].post(url, {'action': 'mark_tenu'}, follow=True)
    assert reponse.redirect_chain[-1][0] == url
    contexte['conseil'].refresh_from_db()
    assert contexte['conseil'].tenu is True
    assert 'Conseil marqué comme tenu' in reponse.content.decode()

    decision = contexte['decisions'][0]
    contexte['client'].post(url, {
        'action': 'save_decisions',
        f'decision_{decision.pk}': 'FELICITE_modifiee' if False else 'REDOUBLEMENT',
        f'appreciation_{decision.pk}': 'Travail irrégulier, doit redoubler.',
        f'mention_{decision.pk}': 'on',
        f'felicitations_{decision.pk}': 'on',
    })
    decision.refresh_from_db()
    assert decision.decision == 'REDOUBLEMENT'
    assert decision.appreciation == 'Travail irrégulier, doit redoubler.'
    assert decision.mention_honneur and decision.felicitations and not decision.encouragements

    # Les décisions non soumises ne bougent pas : la deuxième garde son état d'origine
    autre = contexte['decisions'][1]
    autre.refresh_from_db()
    assert autre.decision == DecisionConseil.DecisionChoices.PASSAGE and autre.appreciation == ''


def test_conseil_create_genere_les_decisions_sans_l_abandon(contexte):
    """Créer un conseil crée une décision par élève actif — jamais pour un élève en abandon."""
    url = reverse('viescolaire:conseil_create')
    assert contexte['client'].get(url).status_code == 200

    reponse = contexte['client'].post(url, {
        'classe': str(contexte['classe'].pk),
        'trimestre': str(contexte['trimestre_2'].pk),
        'date_conseil': '2027-03-28',
        'president': str(contexte['dire'].pk),
    })
    nouveau = ConseilClasse.objects.get(classe=contexte['classe'], trimestre=contexte['trimestre_2'])
    assert reponse.status_code == 302
    assert reponse.url == reverse('viescolaire:conseil_detail', kwargs={'conseil_id': nouveau.pk})
    assert nouveau.date_conseil == datetime.date(2027, 3, 28)
    assert nouveau.president == contexte['dire']
    decisions = nouveau.decisions.select_related('inscription__eleve')
    assert decisions.count() == 3, "l'élève en abandon reste hors conseil"
    assert 'TRAORE' not in {d.inscription.eleve.nom for d in decisions}


def test_conseil_create_doublon_ne_recree_rien(contexte):
    """Un second envoi sur la même classe/trimestre renvoie vers le conseil existant avec un avertissement."""
    deja = baker.make(ConseilClasse, classe=contexte['classe'], trimestre=contexte['trimestre_2'],
                      date_conseil=datetime.date(2027, 3, 20))
    avant = DecisionConseil.objects.count()

    reponse = contexte['client'].post(reverse('viescolaire:conseil_create'), {
        'classe': str(contexte['classe'].pk),
        'trimestre': str(contexte['trimestre_2'].pk),
        'date_conseil': '2027-03-28',
    }, follow=True)
    assert ConseilClasse.objects.filter(classe=contexte['classe'],
                                        trimestre=contexte['trimestre_2']).count() == 1
    assert DecisionConseil.objects.count() == avant
    assert deja.date_conseil == datetime.date(2027, 3, 20), 'le conseil existant n’est pas écrasé'
    assert 'existe déjà' in reponse.content.decode()


def test_conseil_pv_pdf_reprend_les_moyennes_et_les_mentions(contexte, mocker):
    """Le PV PDF porte les élèves, leur moyenne du trimestre et le récapitulatif des mentions."""
    for decision in contexte['decisions']:
        baker.make('pedagogie.MoyenneGenerale', inscription=decision.inscription,
                   trimestre=contexte['trimestre'], moyenne=Decimal('13.50'))
    moteur = mocker.patch.object(vues_conseils, 'WeasyHTML')
    moteur.return_value.write_pdf.return_value = b'%PDF-1.4 pv'

    reponse = contexte['client'].get(reverse('viescolaire:conseil_pv_pdf',
                                             kwargs={'conseil_id': contexte['conseil'].pk}))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content == b'%PDF-1.4 pv'
    assert 'PV_conseil_3e_A_Trimestre_1.pdf' in reponse['Content-Disposition']
    html = moteur.call_args.kwargs['string']
    assert 'OUEDRAOGO' in html and '13,50' in html and 'Mention' in html


def test_conseil_pv_pdf_sans_moteur_previent_au_lieu_d_echouer(contexte, mocker):
    """Sans WeasyPrint, l'utilisateur revient sur le conseil avec un message explicite."""
    mocker.patch.object(vues_conseils, 'WeasyHTML', None)
    reponse = contexte['client'].get(reverse('viescolaire:conseil_pv_pdf',
                                             kwargs={'conseil_id': contexte['conseil'].pk}), follow=True)
    assert reponse.status_code == 200
    assert 'WeasyPrint' in reponse.content.decode()


# ── Appels de décision ───────────────────────────────────────────────────────

def _conteste(contexte, decision, **extra):
    decision.decision = DecisionConseil.DecisionChoices.REDOUBLEMENT
    decision.save(update_fields=['decision'])
    return baker.make(AppelDecision, decision_conseil=decision,
                      motif='Dossier médical', **extra)


def test_appel_list_filtre_par_statut_et_compte_les_attentes(contexte):
    """La liste des appels est cloisonnée à l'établissement et filtrable par statut."""
    attendu = _conteste(contexte, contexte['decisions'][0])
    traite = _conteste(contexte, contexte['decisions'][1],
                       statut=AppelDecision.StatutChoices.TRAITE,
                       issue=AppelDecision.IssueChoices.MAINTENU)

    url = reverse('viescolaire:appel_decision_list')
    reponse = contexte['client'].get(url)
    assert reponse.status_code == 200
    assert {a.pk for a in reponse.context['appels']} == {attendu.pk, traite.pk}
    assert reponse.context['nb_en_attente'] == 1

    filtre = contexte['client'].get(url, {'statut': AppelDecision.StatutChoices.TRAITE})
    assert [a.pk for a in filtre.context['appels']] == [traite.pk]
    assert filtre.context['statut_filter'] == AppelDecision.StatutChoices.TRAITE


def test_appel_list_sans_etablissement_respecte_le_perimetre_tous_cycles(contexte):
    """Un compte sans établissement mais autorisé à tous les cycles conserve son accès réseau."""
    appel = _conteste(contexte, contexte['decisions'][0])
    contexte['dire'].etablissement = None
    contexte['dire'].save(update_fields=['etablissement'])

    reponse = contexte['client'].get(reverse('viescolaire:appel_decision_list'))
    assert reponse.status_code == 200
    assert [a.pk for a in reponse.context['appels']] == [appel.pk]


def test_appel_create_depose_une_contestation(contexte):
    """Le dépôt d'appel exige un motif ; la date ISO est reprise, sinon la date du jour."""
    decision = contexte['decisions'][0]
    decision.decision = DecisionConseil.DecisionChoices.REDOUBLEMENT
    decision.save(update_fields=['decision'])
    url = reverse('viescolaire:appel_decision_create', kwargs={'decision_id': decision.pk})

    formulaire = contexte['client'].get(url)
    assert formulaire.status_code == 200
    assert formulaire.context['today'] == datetime.date.today().isoformat()

    sans_motif = contexte['client'].post(url, {'motif': '   '}, follow=True)
    assert not AppelDecision.objects.exists()
    assert 'motif de contestation est obligatoire' in sans_motif.content.decode()

    contexte['client'].post(url, {'motif': 'Erreur de moyenne', 'date_depot': 'pas-une-date'})
    appel = AppelDecision.objects.get(decision_conseil=decision)
    assert appel.date_depot == datetime.date.today()
    assert appel.depose_par == contexte['dire']
    assert appel.statut == AppelDecision.StatutChoices.EN_ATTENTE


def test_appel_create_refuse_une_decision_non_contestable_ou_deja_contestee(contexte):
    """Seuls redoublement, orientation et exclusion sont contestables, et une seule fois."""
    passage = contexte['decisions'][0]          # PASSAGE par défaut
    refus = contexte['client'].post(
        reverse('viescolaire:appel_decision_create', kwargs={'decision_id': passage.pk}), follow=True)
    assert not AppelDecision.objects.exists()
    assert 'ne peut pas être contestée' in refus.content.decode()

    redoublement = contexte['decisions'][1]
    _conteste(contexte, redoublement)
    encore = contexte['client'].get(
        reverse('viescolaire:appel_decision_create', kwargs={'decision_id': redoublement.pk}), follow=True)
    assert encore.redirect_chain[-1][0] == reverse('viescolaire:conseil_detail',
                                                   kwargs={'conseil_id': contexte['conseil'].pk})
    assert 'Cette décision a déjà fait' in encore.content.decode()


def test_appel_create_ne_touche_pas_une_decision_d_un_autre_etablissement(contexte):
    """Unidentifiant d'une autre école est un 404, pas un accès indirect."""
    autre_etab = baker.make('etablissements.Etablissement', nom='AILLEURS')
    autre_annee = baker.make('parametres.AnneeScolaire', etablissement=autre_etab, est_courante=False)
    autre_trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=autre_annee, nom='Trimestre 1',
                                 date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2026, 12, 31))
    autre_classe = baker.make('parametres.Classe', etablissement=autre_etab, nom='6e A')
    autre_conseil = baker.make(ConseilClasse, classe=autre_classe, trimestre=autre_trimestre,
                               date_conseil=datetime.date(2026, 12, 20))
    autre = baker.make(DecisionConseil, conseil=autre_conseil,
                       inscription=baker.make('inscriptions.Inscription', classe=autre_classe,
                                              annee_scolaire=autre_annee),
                       decision=DecisionConseil.DecisionChoices.EXCLUSION)

    url = reverse('viescolaire:appel_decision_create', kwargs={'decision_id': autre.pk})
    assert contexte['client'].get(url).status_code == 404


def test_appel_traiter_modifie_la_decision_et_cloture(contexte):
    """Instruction : la commission modifie la décision, l'appel passe à « traité » et se date."""
    decision = contexte['decisions'][0]
    appel = _conteste(contexte, decision)
    url = reverse('viescolaire:appel_decision_traiter', kwargs={'appel_id': appel.pk})

    assert contexte['client'].get(url).status_code == 200

    sans_issue = contexte['client'].post(url, {'statut': AppelDecision.StatutChoices.TRAITE}, follow=True)
    assert 'issue est obligatoire' in sans_issue.content.decode()
    appel.refresh_from_db()
    assert appel.statut == AppelDecision.StatutChoices.EN_ATTENTE

    contexte['client'].post(url, {
        'issue': AppelDecision.IssueChoices.MODIFIE,
        'nouvelle_decision': DecisionConseil.DecisionChoices.PASSAGE,
        'observations_commission': 'Résultats en progrès au 2e trimestre.',
        'statut': AppelDecision.StatutChoices.TRAITE,
    })
    appel.refresh_from_db()
    decision.refresh_from_db()
    assert appel.est_traite and appel.traite_par == contexte['dire']
    assert appel.date_traitement == datetime.date.today()
    assert appel.nouvelle_decision == DecisionConseil.DecisionChoices.PASSAGE
    assert decision.decision == DecisionConseil.DecisionChoices.PASSAGE, 'la décision effective suit l’appel'
    assert appel.observations_commission.startswith('Résultats')


def test_appel_deja_traite_est_verrouille(contexte):
    """Un appel clôturé ne se réinstruit pas : retour à la liste avec une information."""
    decision = contexte['decisions'][0]
    appel = _conteste(contexte, decision, statut=AppelDecision.StatutChoices.TRAITE,
                      issue=AppelDecision.IssueChoices.MAINTENU)
    reponse = contexte['client'].post(
        reverse('viescolaire:appel_decision_traiter', kwargs={'appel_id': appel.pk}),
        {'issue': AppelDecision.IssueChoices.ANNULE, 'statut': AppelDecision.StatutChoices.EN_INSTRUCTION},
        follow=True)
    appel.refresh_from_db()
    assert appel.issue == AppelDecision.IssueChoices.MAINTENU
    assert reponse.redirect_chain[-1][0] == reverse('viescolaire:appel_decision_list')
    assert 'déjà traité' in reponse.content.decode()


def test_appel_traiter_ne_franchit_pas_l_etablissement(contexte):
    """Un appel d'une autre école est invisible."""
    autre_etab = baker.make('etablissements.Etablissement', nom='AILLEURS')
    autre_annee = baker.make('parametres.AnneeScolaire', etablissement=autre_etab, est_courante=False)
    autre_trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=autre_annee, nom='Trimestre 1',
                                 date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2026, 12, 31))
    autre_classe = baker.make('parametres.Classe', etablissement=autre_etab, nom='6e A')
    autre_ins = baker.make('inscriptions.Inscription', classe=autre_classe, annee_scolaire=autre_annee)
    autre_decision = baker.make(DecisionConseil,
                                conseil=baker.make(ConseilClasse, classe=autre_classe,
                                                   trimestre=autre_trimestre,
                                                   date_conseil=datetime.date(2026, 12, 20)),
                                inscription=autre_ins)
    appel = baker.make(AppelDecision, decision_conseil=autre_decision, motif='Hors périmètre')

    url = reverse('viescolaire:appel_decision_traiter', kwargs={'appel_id': appel.pk})
    assert contexte['client'].get(url).status_code == 404
