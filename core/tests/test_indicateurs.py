"""Historisation pluriannuelle des indicateurs (5.39.0) : calcul, écarts d'une année sur l'autre, page, commande."""
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core import indicateurs
from core.models import IndicateurAnnee
from parametres.models import TarifScolarite

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement')
    user = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, est_tous_cycles=True, must_change_password=False)
    client.force_login(user)
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A')
    precedente = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026',
                            date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30))
    courante = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                          date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, code='SCOL', actif=True)
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Affecté')

    def inscrire(annee, nom, genre, paye=0, moyenne=None):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Awa', genre=genre, date_naissance=date(2012, 1, 1), photo='')
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee, classe=classe,
                                 statut='AFFECTE', statut_eleve=statut)
        baker.make('parametres.TarifScolarite', etablissement=etab, annee_scolaire=annee, classe=classe,
                   rubrique=rubrique, statut_eleve=statut, montant=Decimal('50000'), actif=True) \
            if not TarifScolarite.objects.filter(annee_scolaire=annee, classe=classe, rubrique=rubrique,
                                                 statut_eleve=statut).exists() else None
        if paye:
            baker.make('finances.Paiement', inscription=inscription, montant=Decimal(paye), rubrique=rubrique,
                       statut_eleve=statut, date_paiement=annee.date_debut, mode_paiement='ESPECES')
        if moyenne is not None:
            trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
                                   date_debut=annee.date_debut, date_fin=annee.date_debut + timedelta(days=60))
            baker.make('pedagogie.MoyenneGenerale', inscription=inscription, trimestre=trimestre, moyenne=Decimal(moyenne))
        return inscription

    # 2025-2026 : 1 élève, payé 50 000, moyenne 8
    inscrire(precedente, 'ANCIEN', 'M', paye=50000, moyenne='8.00')
    # 2026-2027 : 2 élèves (1 fille), l'un payé, moyenne 12 ; 3 pointages dont 1 absence
    i1 = inscrire(courante, 'NOUVEAU', 'F', paye=25000, moyenne='12.00')
    inscrire(courante, 'AUTRE', 'M')
    jour = courante.date_debut
    for statut_presence in ('PRESENT', 'PRESENT', 'ABSENT'):
        appel = baker.make('presences.Appel', classe=classe, annee_scolaire=courante, date=jour)
        baker.make('presences.Presence', appel=appel, inscription=i1, statut=statut_presence)
    return {'etab': etab, 'precedente': precedente, 'courante': courante, 'classe': classe}


def test_calcul_des_indicateurs(ecole):
    mesures = indicateurs.calculer(ecole['etab'], ecole['courante'])
    assert (mesures['effectif'], mesures['effectif_filles'], mesures['effectif_garcons']) == (2, 1, 1)
    assert mesures['moyenne_generale'] == Decimal('12')
    assert mesures['taux_reussite'] == 100.0                    # seul élève noté, moyenne >= 10
    assert mesures['taux_recouvrement'] == 25.0                 # 25 000 payés sur 100 000 attendus
    assert mesures['taux_absenteisme'] == 33.33                 # 1 absence sur 3 pointages
    vide = indicateurs.calculer(ecole['etab'], baker.make('parametres.AnneeScolaire', etablissement=ecole['etab'],
                                                         libelle='2030-2031', date_debut=date(2030, 10, 1),
                                                         date_fin=date(2031, 6, 30)))
    assert (vide['effectif'], vide['taux_recouvrement'], vide['taux_reussite']) == (0, None, None)


def test_mise_a_jour_et_ecarts(ecole):
    indicateurs.mettre_a_jour(ecole['etab'])
    assert IndicateurAnnee.objects.filter(etablissement=ecole['etab']).count() == 2
    lignes = indicateurs.evolution(ecole['etab'])
    assert [l.annee_scolaire.libelle for l in lignes] == ['2025-2026', '2026-2027']
    assert lignes[0].ecarts['effectif'] is None
    assert (lignes[1].ecarts['effectif'], lignes[1].ecarts['taux_recouvrement']) == (1, Decimal('-75.00'))  # 100 % → 25 %
    # Recalcul idempotent : une seule ligne par année
    indicateurs.mettre_a_jour(ecole['etab'])
    assert IndicateurAnnee.objects.filter(etablissement=ecole['etab']).count() == 2


def test_page_et_commande(client, ecole):
    url = reverse('core:indicateurs_evolution')
    assert 'Aucun indicateur' in client.get(url).content.decode()
    assert client.post(url).status_code == 302
    html = client.get(url).content.decode()
    assert '2025-2026' in html and '2026-2027' in html and '25,0 %' in html
    IndicateurAnnee.objects.all().delete()
    out = StringIO()
    call_command('historiser_indicateurs', stdout=out)
    assert "2 année(s) d'indicateurs" in out.getvalue()
    assert IndicateurAnnee.objects.count() == 2
    client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=ecole['etab'], must_change_password=False))
    assert client.get(url).status_code == 403


def test_nouvelle_annee_sans_donnees(ecole):
    baker.make('parametres.AnneeScolaire', etablissement=ecole['etab'], libelle='2027-2028',
               date_debut=date(2027, 10, 1), date_fin=date(2028, 6, 30))
    lignes = indicateurs.mettre_a_jour(ecole['etab'])
    assert [l.effectif for l in lignes][-1] == 0 and lignes[-1].calcule_le <= timezone.now()


@pytest.mark.django_db
def test_evolution_etablissement_refuse_un_compte_restreint_a_un_cycle(client, ecole):
    cycle = ecole['classe'].cycle
    baker.make('parametres.Cycle', etablissement=ecole['etab'], code='SEC', nom='Secondaire')
    utilisateur = baker.make('accounts.User', role='DIRECTEUR', etablissement=ecole['etab'], must_change_password=False)
    utilisateur.cycles.add(cycle)
    client.force_login(utilisateur)

    url = reverse('core:indicateurs_evolution')
    assert client.get(url).status_code == 403
    assert client.post(url).status_code == 403
    assert not IndicateurAnnee.objects.exists()
