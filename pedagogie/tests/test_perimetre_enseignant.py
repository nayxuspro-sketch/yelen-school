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
    return {'etab': etab, 'classe_a': classe_a, 'classe_b': classe_b, 'ens': ens, 'evals': evals}


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
