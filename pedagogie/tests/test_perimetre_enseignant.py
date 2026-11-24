"""Périmètre d'un enseignant sur les évaluations : ses enseignements (fiche du personnel reliée par e-mail)."""
import pytest
from django.urls import reverse
from model_bakery import baker

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexte():
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe_a, classe_b = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, _quantity=2)
    justin = baker.make('personnel.MembrePersonnel', etablissement=etab, email='Justin.Kabore@ecole.bf')
    collegue = baker.make('personnel.MembrePersonnel', etablissement=etab, email='collegue@ecole.bf')
    ens = {
        'sien': baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe_a, personnel=justin, est_actif=True),
        'collegue': baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe_b, personnel=collegue, est_actif=True),
        'orphelin': baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe_b, personnel=None, est_actif=True),
    }
    evals = {cle: baker.make('pedagogie.Evaluation', enseignement=e) for cle, e in ens.items()}
    return {'etab': etab, 'annee': annee, 'classe_a': classe_a, 'classe_b': classe_b, 'ens': ens, 'evals': evals}


def _enseignant(client, etab, email):
    from parametres.models import Cycle

    user = baker.make('accounts.User', etablissement=etab, role='ENSEIGNANT', email=email,
                      must_change_password=False)
    user.cycles.set(Cycle.objects.filter(etablissement=etab))
    client.force_login(user)
    return client


def test_enseignant_relie_saisit_ses_notes_et_pas_celles_d_un_collegue(client, contexte):
    c = _enseignant(client, contexte['etab'], 'justin.kabore@ecole.bf')          # casse différente de la fiche

    assert c.get(reverse('pedagogie:evaluation_saisie', kwargs={'pk': contexte['evals']['sien'].pk})).status_code == 200
    refus = c.get(reverse('pedagogie:evaluation_saisie', kwargs={'pk': contexte['evals']['collegue'].pk}))
    assert refus.status_code == 302 and refus.url == reverse('pedagogie:evaluation_list')
    html = c.get(reverse('pedagogie:evaluation_list')).content.decode()
    assert 'Saisie des notes refusée' in html and 'ne vous est pas attribué' in html


def test_enseignant_sans_fiche_est_guide_et_ne_voit_rien(client, contexte):
    c = _enseignant(client, contexte['etab'], 'inconnu@ecole.bf')

    refus = c.get(reverse('pedagogie:evaluation_saisie', kwargs={'pk': contexte['evals']['orphelin'].pk}))
    assert refus.status_code == 302
    html = c.get(reverse('pedagogie:evaluation_list')).content.decode()
    assert 'aucune fiche du personnel' in html and '(inconnu@ecole.bf)' in html
    assert 'evaluations/' + str(contexte['evals']['orphelin'].pk) not in html   # plus d'accès aux enseignements sans titulaire
    assert c.get(reverse('pedagogie:saisie_classe_select')).context['classes'].count() == 0


def test_selection_par_classe_limitee_aux_enseignements_du_professeur(client, contexte):
    c = _enseignant(client, contexte['etab'], 'justin.kabore@ecole.bf')

    assert [cl.pk for cl in c.get(reverse('pedagogie:saisie_classe_select')).context['classes']] == [contexte['classe_a'].pk]
    rapide = c.get(reverse('pedagogie:saisie_rapide_classe', kwargs={'class_id': contexte['classe_b'].pk}))
    assert rapide.status_code == 200 and rapide.context['par_matiere'] == {}
    form = c.get(reverse('pedagogie:evaluation_create')).context['form']
    assert [e.pk for e in form.fields['enseignement'].queryset] == [contexte['ens']['sien'].pk]
    refus = c.get(reverse('pedagogie:evaluation_update', kwargs={'pk': contexte['evals']['collegue'].pk}))
    assert refus.status_code == 302 and refus.url == reverse('pedagogie:evaluation_list')


def test_releve_de_notes_limite_aux_classes_et_disciplines_du_professeur(client, contexte):
    """Relevé de notes : un enseignant ne choisit que ses classes et, dans chacune, que ses disciplines ;
    un enseignement forgé dans l'URL est refusé (écran et exports PDF). La direction garde la vue complète."""
    from django.contrib.messages import get_messages
    ens, annee = contexte['ens'], contexte['ens']['sien'].annee_scolaire
    baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=contexte['classe_a'],
               personnel=ens['collegue'].personnel, est_actif=True)             # le collègue enseigne aussi en classe A
    url = reverse('pedagogie:releve_notes')
    c = _enseignant(client, contexte['etab'], 'justin.kabore@ecole.bf')

    ctx = c.get(url, {'annee': annee.pk}).context
    assert [cl.pk for cl in ctx['classes']] == [contexte['classe_a'].pk]
    ctx = c.get(url, {'annee': annee.pk, 'classe': contexte['classe_a'].pk}).context
    assert [e.pk for e in ctx['enseignements']] == [ens['sien'].pk]
    ctx = c.get(url, {'annee': annee.pk, 'classe': contexte['classe_a'].pk, 'enseignement': ens['sien'].pk}).context
    assert ctx['enseignement'] == ens['sien'] and ctx['table'] is not None

    forge = c.get(url, {'annee': annee.pk, 'classe': contexte['classe_b'].pk, 'enseignement': ens['collegue'].pk})
    assert forge.context['classe'] is None and forge.context['table'] is None
    assert 'ne vous est pas attribué' in str(list(get_messages(forge.wsgi_request))[0])
    for nom_url in ('pedagogie:releve_notes_pdf', 'pedagogie:fiche_discipline_pdf'):
        refus = c.get(reverse(nom_url), {'annee': annee.pk, 'enseignement': ens['collegue'].pk})
        assert refus.status_code == 302 and refus.url == url
        assert 'ne vous est pas attribué' in str(list(get_messages(refus.wsgi_request))[0])

    client.force_login(baker.make('accounts.User', etablissement=contexte['etab'], role='DIRECTEUR', must_change_password=False))
    ctx = client.get(url, {'annee': annee.pk, 'classe': contexte['classe_a'].pk}).context
    assert ctx['classes'].count() == 2 and ctx['enseignements'].count() == 2


def test_selection_par_classe_limitee_a_l_etablissement_du_personnel(client, contexte):
    """Secrétaire, censeur… : la sélection de classe pour la saisie des notes ne montre que les classes de
    leur établissement (elle listait toutes les classes de tous les établissements)."""
    autre = baker.make('etablissements.Etablissement', code='AUT', nom='Autre collège')
    baker.make('parametres.Classe', etablissement=autre, nom='6e Z', actif=True)
    user = baker.make('accounts.User', etablissement=contexte['etab'], role='SECRETAIRE',
                      est_tous_cycles=True, must_change_password=False)
    client.force_login(user)
    classes = client.get(reverse('pedagogie:saisie_classe_select')).context['classes']
    assert {cl.etablissement_id for cl in classes} == {contexte['etab'].pk}
    assert '6e Z' not in [cl.nom for cl in classes]


# ── « Planifier un devoir » : une liste vide doit dire pourquoi ───────────────────────────────

@pytest.mark.django_db
def test_planifier_un_devoir_explique_une_fiche_non_reliee(client):
    """Fiche du personnel sans l'e-mail du compte : la liste serait vide sans explication."""
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe,
               personnel=baker.make('personnel.MembrePersonnel', etablissement=etab, email='autre@ecole.bf'),
               est_actif=True)
    c = _enseignant(client, etab, 'prof@ecole.bf')

    html = c.get(reverse('pedagogie:evaluation_create')).content.decode()
    assert 'aucune fiche du personnel ne porte' in html and '(prof@ecole.bf)' in html


@pytest.mark.django_db
def test_planifier_un_devoir_explique_une_absence_d_affectation(client):
    """Fiche bien reliée mais aucun enseignement : l'administration doit affecter les disciplines."""
    etab = baker.make('etablissements.Etablissement')
    baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    baker.make('personnel.MembrePersonnel', etablissement=etab, email='prof@ecole.bf')
    c = _enseignant(client, etab, 'prof@ecole.bf')

    html = c.get(reverse('pedagogie:evaluation_create')).content.decode()
    assert 'aucun enseignement ne vous est attribué' in html


@pytest.mark.django_db
def test_planifier_un_devoir_propose_les_disciplines_du_professeur(client, contexte):
    """Ses disciplines sont proposées : le message ne porte que sur les périodes, s'il en manque."""
    from datetime import date, timedelta
    auj = date.today()
    baker.make('parametres.PeriodeEvaluation', etablissement=contexte['etab'],
               annee_scolaire=contexte['annee'],
               numero=1, nom='Trimestre 1',
               date_debut=auj - timedelta(days=30), date_fin=auj + timedelta(days=30))
    c = _enseignant(client, contexte['etab'], 'justin.kabore@ecole.bf')

    response = c.get(reverse('pedagogie:evaluation_create'))
    assert response.context['motif_liste_vide'] is None
    assert response.context['form'].fields['enseignement'].queryset.count() == 1


@pytest.mark.django_db
def test_planifier_un_devoir_explique_l_absence_de_periode(client):
    """Sans période d'évaluation, le champ Trimestre est vide : l'écran doit le dire."""
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, email='eps@ecole.bf')
    baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe, personnel=prof, est_actif=True)
    c = _enseignant(client, etab, 'eps@ecole.bf')

    response = c.get(reverse('pedagogie:evaluation_create'))
    # Le message est échappé dans le HTML (apostrophes typographiques rendues en entités)
    assert "période d" in response.context['motif_liste_vide'] and 'Périodes' in response.context['motif_liste_vide']
    assert 'alert-warning' in response.content.decode()


@pytest.mark.django_db
def test_planifier_un_devoir_sans_message_quand_les_periodes_existent(client, contexte):
    """Cas nominal complet : périodes et enseignements présents, aucune alerte."""
    from datetime import date, timedelta
    auj = date.today()
    baker.make('parametres.PeriodeEvaluation', etablissement=contexte['etab'],
               annee_scolaire=contexte['etab'].annees_scolaires.get(), numero=1, nom='Trimestre 1',
               date_debut=auj - timedelta(days=30), date_fin=auj + timedelta(days=30))
    c = _enseignant(client, contexte['etab'], 'justin.kabore@ecole.bf')

    response = c.get(reverse('pedagogie:evaluation_create'))
    assert response.context['motif_liste_vide'] is None


@pytest.mark.django_db
def test_planifier_un_devoir_signale_une_affectation_sans_enseignant(client):
    """Le cas le plus courant : l'affectation existe, mais le champ « Enseignant » est resté vide.

    Le message doit désigner cette cause précise — et non « aucun enseignement attribué »,
    qui envoyait l'administration créer un doublon au lieu de compléter la ligne existante.
    """
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True,
                       libelle='2026-2027')
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    baker.make('personnel.MembrePersonnel', etablissement=etab, email='eps@ecole.bf')
    baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe, personnel=None)
    c = _enseignant(client, etab, 'eps@ecole.bf')

    motif = c.get(reverse('pedagogie:evaluation_create')).context['motif_liste_vide']
    assert "ne portent pas votre nom" in motif and '2026-2027' in motif
    assert 'aucun enseignement ne vous est attribué' not in motif


@pytest.mark.django_db
def test_planifier_un_devoir_sans_affectation_garde_le_message_general(client):
    """Aucune affectation du tout : le message général reste le bon."""
    etab = baker.make('etablissements.Etablissement')
    baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC')
    baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    baker.make('personnel.MembrePersonnel', etablissement=etab, email='paul@ecole.bf')
    c = _enseignant(client, etab, 'paul@ecole.bf')

    motif = c.get(reverse('pedagogie:evaluation_create')).context['motif_liste_vide']
    assert 'aucun enseignement ne vous est attribué' in motif
