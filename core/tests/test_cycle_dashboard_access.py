"""Le tableau d'accueil et la recherche globale respectent les cycles autorisés."""
import datetime

import pytest
from django.urls import reverse
from model_bakery import baker

pytestmark = pytest.mark.django_db


def test_accueil_et_recherche_ne_revelent_pas_les_autres_cycles(client):
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True,
                       date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2027, 6, 30))
    cycle_autorise = baker.make('parametres.Cycle', etablissement=etab, nom='Primaire', code='PRIM')
    cycle_interdit = baker.make('parametres.Cycle', etablissement=etab, nom='Secondaire', code='SEC')
    classe_autorisee = baker.make('parametres.Classe', etablissement=etab, cycle=cycle_autorise,
                                  nom='CLOISON-PRIM', actif=True)
    classe_interdite = baker.make('parametres.Classe', etablissement=etab, cycle=cycle_interdit,
                                  nom='CLOISON-SEC', actif=True)
    eleve_visible = baker.make('inscriptions.Eleve', nom='CLOISON', prenom='Visible')
    eleve_cache = baker.make('inscriptions.Eleve', nom='CLOISON', prenom='Secret')
    baker.make('inscriptions.Inscription', eleve=eleve_visible, classe=classe_autorisee,
               annee_scolaire=annee, statut='AFFECTE')
    baker.make('inscriptions.Inscription', eleve=eleve_cache, classe=classe_interdite,
               annee_scolaire=annee, statut='AFFECTE')

    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    user.cycles.add(cycle_autorise)
    client.force_login(user)

    accueil = client.get('/')
    assert accueil.status_code == 200
    assert accueil.context['inscriptions_annee'] == 1
    assert accueil.context['total_eleves'] == 1
    assert accueil.context['nb_classes'] == 1
    assert [ligne['cycle'].pk for ligne in accueil.context['repartition_cycles']] == [cycle_autorise.pk]

    recherche = client.get(reverse('core:recherche'), {'q': 'CLOISON'})
    html = recherche.content.decode()
    assert 'CLOISON Visible' in html and 'CLOISON-PRIM' in html
    assert 'CLOISON Secret' not in html and 'CLOISON-SEC' not in html
