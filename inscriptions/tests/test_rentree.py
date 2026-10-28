"""Lot E — rentrée et fin d'année : passage de classe depuis les décisions du conseil, réinscription par établissement,
clôture d'année appliquée, capacité des classes contrôlée, détection des homonymes."""
import json
from datetime import date
from html import unescape

import pytest
from django.urls import reverse
from model_bakery import baker

from inscriptions import services
from inscriptions.forms import InscriptionForm, TransfertClasseForm
from inscriptions.models import Inscription
from parametres.niveaux import cle_niveau, niveau_suivant, rang_niveau
from viescolaire.models import ConseilClasse

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', code='SAV')
    user = baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False)
    client.force_login(user)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026',
                       date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30), est_courante=True)
    suivante = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027',
                          date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30), est_courante=False)
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Collège')
    sixieme = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A', niveau='6ème', capacite_max=50, actif=True)
    cinquieme = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='5e A', niveau='5ème', capacite_max=50, actif=True)
    troisieme = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', niveau='3ème', capacite_max=50, actif=True)
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Affecté', actif=True)
    statut_prive = baker.make('parametres.StatutEleve', etablissement=etab, nom='Non affecté', actif=True)
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=3, nom='T3',
                           date_debut=date(2026, 4, 1), date_fin=date(2026, 6, 30))

    def inscrire(nom, classe, decision=None, **champs):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Test', date_naissance=date(2012, 1, 1))
        ins = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee,
                         statut_eleve=statut, **{'statut': 'AFFECTE', **champs})
        if decision:
            conseil, _ = ConseilClasse.objects.get_or_create(classe=classe, trimestre=trimestre,
                                                             defaults={'date_conseil': date(2026, 6, 20)})
            baker.make('viescolaire.DecisionConseil', conseil=conseil, inscription=ins, decision=decision)
        return ins

    return {
        'etab': etab, 'user': user, 'annee': annee, 'suivante': suivante, 'cycle': cycle,
        'sixieme': sixieme, 'cinquieme': cinquieme, 'troisieme': troisieme, 'statut': statut, 'statut_prive': statut_prive,
        'awa': inscrire('AWA', sixieme, 'PASSAGE'),
        'issa': inscrire('ISSA', sixieme, 'REDOUBLEMENT'),
        'moussa': inscrire('MOUSSA', sixieme),
        'fanta': inscrire('FANTA', troisieme, 'PASSAGE'),
        'exclu': inscrire('EXCLU', sixieme, 'EXCLUSION'),
        'parti': inscrire('PARTI', sixieme, statut='ABANDON'),
    }


# ── Niveaux ───────────────────────────────────────────────────────────────────

def test_niveaux_canoniques():
    assert [cle_niveau(n) for n in ('6ème A', 'Tle D', 'Terminale', 'CM2', '1ère', 'Atelier')] == ['6', 'T', 'T', 'CM2', '1', 'ATELIER']
    assert niveau_suivant('CM2') == '6' and niveau_suivant('6ème') == '5' and niveau_suivant('3ème') == '2'
    assert niveau_suivant('Terminale') is None and niveau_suivant('Atelier') is None
    assert sorted(['3ème', 'CP1', '6ème', 'Atelier'], key=rang_niveau) == ['CP1', '6ème', '3ème', 'Atelier']


# ── E1 / E3 : passage de classe ───────────────────────────────────────────────

def test_liste_propose_la_classe_selon_la_decision(client, ecole):
    """Passage → classe du niveau supérieur ; redoublement → même classe ; exclusion ou niveau sans classe → aucune ;
    les abandons et les élèves déjà inscrits pour l'année suivante n'apparaissent pas."""
    services.reinscrire(ecole['moussa'], ecole['cinquieme'], ecole['suivante'])
    reponse = client.get(reverse('inscriptions:reinscription_list'))
    lignes = {l['inscription'].eleve.nom: l for l in reponse.context['lignes']}

    assert set(lignes) == {'AWA', 'ISSA', 'FANTA', 'EXCLU'}
    assert lignes['AWA']['proposee'] == ecole['cinquieme'] and lignes['AWA']['decision'] == 'Passage'
    assert lignes['ISSA']['proposee'] == ecole['sixieme']
    assert lignes['FANTA']['proposee'] is None and lignes['EXCLU']['proposee'] is None
    html = reponse.content.decode()
    assert f'<option value="{ecole["cinquieme"].pk}" selected>' in html
    assert 'Inscrire les élèves cochés pour 2026-2027' in html


def test_passage_en_lot_reprend_statut_et_redoublement(client, ecole):
    reponse = client.post(reverse('inscriptions:passage_classe'), {
        'inscriptions': [str(ecole['awa'].pk), str(ecole['issa'].pk)],
        f'classe_{ecole["awa"].pk}': str(ecole['cinquieme'].pk),
        f'classe_{ecole["issa"].pk}': str(ecole['sixieme'].pk),
    })
    assert reponse.status_code == 302

    awa = Inscription.objects.get(eleve=ecole['awa'].eleve, annee_scolaire=ecole['suivante'])
    issa = Inscription.objects.get(eleve=ecole['issa'].eleve, annee_scolaire=ecole['suivante'])
    assert awa.classe == ecole['cinquieme'] and awa.statut_eleve == ecole['statut'] and not awa.est_redoublant
    assert issa.classe == ecole['sixieme'] and issa.est_redoublant and issa.classe_redoublee == '6e A'
    awa.eleve.refresh_from_db()
    assert (awa.eleve.last_classe, awa.eleve.last_annee) == ('5e A', '2026-2027')
    messages = [m.message for m in client.get(reverse('inscriptions:reinscription_list')).context['messages']]
    assert '2 élève(s) inscrit(s) pour 2026-2027.' in messages


def test_passage_en_lot_signale_les_refus_sans_bloquer_les_autres(client, ecole):
    ecole['cinquieme'].capacite_max = 1
    ecole['cinquieme'].save()
    client.post(reverse('inscriptions:passage_classe'), {
        'inscriptions': [str(ecole['awa'].pk), str(ecole['moussa'].pk), str(ecole['fanta'].pk), 'pas-un-uuid'],
        f'classe_{ecole["awa"].pk}': str(ecole['cinquieme'].pk),
        f'classe_{ecole["moussa"].pk}': str(ecole['cinquieme'].pk),
    })
    messages = [m.message for m in client.get(reverse('inscriptions:reinscription_list')).context['messages']]

    assert Inscription.objects.filter(annee_scolaire=ecole['suivante']).count() == 1
    assert '1 élève(s) inscrit(s) pour 2026-2027.' in messages
    assert any(m.startswith('MOUSSA TEST : Classe 5e A complète : 1/1 places occupées') for m in messages)
    assert 'FANTA TEST : aucune classe de destination choisie.' in messages


def test_reinscrire_un_eleve_avec_statut_choisi(client, ecole):
    url = reverse('inscriptions:reinscrire_eleve', kwargs={'pk': ecole['awa'].eleve.pk})
    html = client.get(url).content.decode()
    assert f'<option value="{ecole["cinquieme"].pk}" selected>' in html
    assert '6e A · Passage' in html

    reponse = client.post(url, {'classe': str(ecole['cinquieme'].pk), 'statut_eleve': str(ecole['statut_prive'].pk)})
    assert reponse.status_code == 302
    nouvelle = Inscription.objects.get(eleve=ecole['awa'].eleve, annee_scolaire=ecole['suivante'])
    assert nouvelle.statut_eleve == ecole['statut_prive'] and nouvelle.classe == ecole['cinquieme']

    doublon = client.post(url, {'classe': str(ecole['cinquieme'].pk)})
    assert doublon.status_code == 200 and Inscription.objects.filter(annee_scolaire=ecole['suivante']).count() == 1
    assert 'AWA TEST est déjà inscrit(e) pour 2026-2027.' in unescape(doublon.content.decode())


def test_reinscrire_refuse_une_classe_d_un_autre_etablissement(ecole):
    autre = baker.make('parametres.Classe', niveau='5ème', capacite_max=50, actif=True)
    with pytest.raises(services.InscriptionImpossible, match="n'appartient pas"):
        services.reinscrire(ecole['awa'], autre, ecole['suivante'])


# ── E2 : périmètre établissement ──────────────────────────────────────────────

def test_reinscription_utilise_l_annee_courante_de_l_etablissement(client, ecole):
    """Une autre école avec sa propre année courante ne change ni l'année ni la liste affichées."""
    autre = baker.make('etablissements.Etablissement')
    annee_autre = baker.make('parametres.AnneeScolaire', etablissement=autre, libelle='2024-2025',
                             date_debut=date(2024, 10, 1), date_fin=date(2025, 6, 30), est_courante=True)
    baker.make('parametres.AnneeScolaire', etablissement=autre, libelle='2025-2026 bis',
               date_debut=date(2025, 10, 2), date_fin=date(2026, 6, 30), est_courante=False)
    classe_autre = baker.make('parametres.Classe', etablissement=autre, niveau='6ème', actif=True)
    baker.make('inscriptions.Inscription', classe=classe_autre, annee_scolaire=annee_autre, statut='AFFECTE',
               eleve=baker.make('inscriptions.Eleve', nom='AILLEURS', date_naissance=date(2012, 1, 1)))

    contexte = client.get(reverse('inscriptions:reinscription_list')).context
    assert contexte['annee_courante'] == ecole['annee'] and contexte['annee_suivante'] == ecole['suivante']
    assert 'AILLEURS' not in {l['inscription'].eleve.nom for l in contexte['lignes']}
    assert services.annee_suivante(annee_autre).libelle == '2025-2026 bis'


# ── E4 : clôture d'année ──────────────────────────────────────────────────────

def test_cloture_annee_verrouille_inscriptions_et_periodes(client, ecole):
    from pedagogie.models import Trimestre
    passee = baker.make('parametres.AnneeScolaire', etablissement=ecole['etab'], libelle='2024-2025',
                        date_debut=date(2024, 10, 1), date_fin=date(2025, 6, 30), est_courante=False)
    periode = baker.make('parametres.PeriodeEvaluation', etablissement=ecole['etab'], annee_scolaire=passee,
                         nom='Trimestre 1', numero=1, date_debut=date(2024, 10, 1), date_fin=date(2024, 12, 20), cloturee=False)
    ancienne = baker.make('inscriptions.Inscription', classe=ecole['sixieme'], annee_scolaire=passee, statut='AFFECTE',
                          eleve=baker.make('inscriptions.Eleve', date_naissance=date(2012, 1, 1)))

    # L'année courante ne se clôture pas.
    refus = client.post(reverse('parametres:annee_cloture', kwargs={'pk': ecole['annee'].pk}))
    ecole['annee'].refresh_from_db()
    assert refus.status_code == 204 and not ecole['annee'].cloturee
    assert 'Impossible de clôturer' in json.loads(refus['HX-Trigger'])['showToast']['message']

    reponse = client.post(reverse('parametres:annee_cloture', kwargs={'pk': passee.pk}))
    passee.refresh_from_db()
    periode.refresh_from_db()
    assert reponse.status_code == 204 and 'parametreUpdated' in reponse['HX-Trigger']
    assert passee.cloturee and periode.cloturee
    assert Trimestre.objects.get(annee_scolaire=passee, numero=1).verrouille

    # Inscriptions verrouillées : formulaire, transfert, abandon, réinscription vers une année clôturée.
    form = InscriptionForm({'eleve': ancienne.eleve.pk, 'annee_scolaire': passee.pk, 'classe': ecole['cinquieme'].pk,
                            'date_inscription': '2024-10-01'}, etablissement=ecole['etab'])
    assert not form.is_valid() and 'est clôturée' in form.errors['annee_scolaire'][0]
    client.post(reverse('inscriptions:transfert_classe', kwargs={'pk': ancienne.pk}), {'classe': ecole['cinquieme'].pk})
    client.post(reverse('inscriptions:marquer_abandon', kwargs={'pk': ancienne.pk}))
    ancienne.refresh_from_db()
    assert ancienne.classe == ecole['sixieme'] and ancienne.statut == 'AFFECTE'
    with pytest.raises(services.InscriptionImpossible, match='est clôturée'):
        services.reinscrire(ecole['awa'], ecole['cinquieme'], passee)

    # Une année clôturée ne devient pas courante ; la réouverture ne rouvre pas les périodes.
    client.post(reverse('parametres:annee_set_courante', kwargs={'pk': passee.pk}))
    passee.refresh_from_db()
    assert not passee.est_courante
    client.post(reverse('parametres:annee_cloture', kwargs={'pk': passee.pk}))
    passee.refresh_from_db()
    periode.refresh_from_db()
    assert not passee.cloturee and periode.cloturee
    assert 'Clôturer' in client.get(reverse('parametres:annee_list')).content.decode()


# ── E5 : capacité des classes ─────────────────────────────────────────────────

def test_capacite_controlee_a_l_inscription_et_au_transfert(ecole):
    ecole['sixieme'].capacite_max = 4  # AWA, ISSA, MOUSSA, EXCLU (PARTI en abandon ne compte pas)
    ecole['sixieme'].save()
    assert services.effectif(ecole['sixieme'], ecole['annee']) == 4
    nouveau = baker.make('inscriptions.Eleve', date_naissance=date(2012, 1, 1))

    form = InscriptionForm({'eleve': nouveau.pk, 'annee_scolaire': ecole['annee'].pk, 'classe': ecole['sixieme'].pk,
                            'date_inscription': '2025-10-01'}, etablissement=ecole['etab'])
    assert not form.is_valid()
    assert form.errors['classe'][0].startswith('Classe 6e A complète : 4/4 places occupées pour 2025-2026.')

    # Modifier une inscription déjà dans la classe complète reste possible (elle ne se compte pas elle-même).
    modif = InscriptionForm({'eleve': ecole['awa'].eleve.pk, 'annee_scolaire': ecole['annee'].pk, 'classe': ecole['sixieme'].pk,
                             'date_inscription': '2025-10-01', 'observations': 'RAS'},
                            instance=ecole['awa'], etablissement=ecole['etab'])
    assert modif.is_valid(), modif.errors

    transfert = TransfertClasseForm({'classe': ecole['sixieme'].pk}, inscription=ecole['fanta'], etablissement=ecole['etab'])
    assert not transfert.is_valid() and 'complète' in transfert.errors['classe'][0]


# ── E6 : homonymes ────────────────────────────────────────────────────────────

def test_creation_eleve_signale_l_homonyme_puis_confirme(client, ecole):
    existant = ecole['awa'].eleve
    donnees = {'nom': 'awa ', 'prenom': 'test', 'genre': existant.genre, 'date_naissance': '2012-01-01',
               'lieu_naissance': 'Ouagadougou', 'nationalite': 'Burkinabè', 'lieu_residence': 'Secteur 30'}

    reponse = client.post(reverse('inscriptions:eleve_create'), donnees)
    html = unescape(reponse.content.decode())
    assert reponse.status_code == 200 and 'Homonyme détecté' in html and existant.matricule in html
    assert 'name="confirmer_homonyme" value="1"' in html
    assert not Inscription.objects.filter(eleve__nom='awa').exists()

    confirme = client.post(reverse('inscriptions:eleve_create'), {**donnees, 'confirmer_homonyme': '1'})
    assert confirme.status_code == 302
    assert existant.__class__.objects.filter(nom__iexact='awa', prenom__iexact='test').count() == 2


def test_homonyme_d_un_autre_etablissement_non_signale(client, ecole):
    autre_classe = baker.make('parametres.Classe', niveau='6ème', actif=True)
    baker.make('inscriptions.Inscription', classe=autre_classe, annee_scolaire=ecole['annee'],
               eleve=baker.make('inscriptions.Eleve', nom='DIALLO', prenom='Sita', date_naissance=date(2013, 5, 5)))
    reponse = client.post(reverse('inscriptions:eleve_create'), {
        'nom': 'DIALLO', 'prenom': 'Sita', 'genre': 'F', 'date_naissance': '2013-05-05', 'lieu_naissance': 'Bobo',
        'nationalite': 'Burkinabè', 'lieu_residence': 'Secteur 1'})
    assert reponse.status_code == 302
