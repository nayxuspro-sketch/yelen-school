"""Lot I — I2 santé / personnes autorisées sur la fiche élève, I4 pré-inscriptions."""
import datetime as dt
from html import unescape

import pytest
from django.urls import reverse
from model_bakery import baker

from inscriptions.models import Eleve, Inscription, PreInscription
from inscriptions.preinscriptions import inscrire, synthese_par_classe

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', code='SAV')
    user = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False)
    client.force_login(user)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=dt.date(2026, 10, 1), date_fin=dt.date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6ème A', capacite_max=2, actif=True)
    return {'etab': etab, 'user': user, 'annee': annee, 'classe': classe}


# ── I2 ──────────────────────────────────────────────────────────────

class TestSante:
    def test_formulaire_et_fiche(self, client, ecole):
        html = unescape(client.get(reverse('inscriptions:eleve_create')).content.decode())
        for champ in ('groupe_sanguin', 'allergies', 'informations_medicales', 'medecin_traitant', 'personnes_autorisees'):
            assert html.count(f'name="{champ}"') == 1
        reponse = client.post(reverse('inscriptions:eleve_create'), {
            'nom': 'OUEDRAOGO', 'prenom': 'Awa', 'genre': 'F', 'date_naissance': '2014-05-02', 'lieu_naissance': 'Ouaga',
            'nationalite': 'Burkinabè', 'lieu_residence': 'Tampouy', 'groupe_sanguin': 'O+', 'allergies': 'Arachide',
            'informations_medicales': 'Asthme — ventoline dans le sac', 'medecin_traitant': 'CSPS Tampouy 70 11 22 33',
            'personnes_autorisees': 'KABORE Issa — oncle — 76 00 00 01',
        })
        assert reponse.status_code == 302
        eleve = Eleve.objects.get(nom='OUEDRAOGO')
        assert eleve.groupe_sanguin == 'O+' and eleve.allergies == 'Arachide'
        fiche = unescape(client.get(reverse('inscriptions:eleve_detail', args=[eleve.pk])).content.decode())
        assert 'Santé & personnes autorisées' in fiche and 'Arachide' in fiche and 'KABORE Issa' in fiche
        assert 'ventoline' in fiche and 'CSPS Tampouy' in fiche

    def test_fiche_sans_donnees_sante(self, client, ecole):
        eleve = baker.make('inscriptions.Eleve', photo='')
        fiche = unescape(client.get(reverse('inscriptions:eleve_detail', args=[eleve.pk])).content.decode())
        assert 'Non renseigné' in fiche and 'Aucune personne déclarée' in fiche

    def test_groupe_sanguin_invalide_refuse(self, client, ecole):
        reponse = client.post(reverse('inscriptions:eleve_create'), {
            'nom': 'X', 'prenom': 'Y', 'genre': 'M', 'date_naissance': '2014-05-02', 'lieu_naissance': 'Ouaga',
            'nationalite': 'Burkinabè', 'lieu_residence': 'Tampouy', 'groupe_sanguin': 'Z+',
        })
        assert reponse.status_code == 200 and not Eleve.objects.filter(nom='X').exists()


# ── I4 ──────────────────────────────────────────────────────────────

def _demande(ecole, **extra):
    base = dict(etablissement=ecole['etab'], annee_scolaire=ecole['annee'], classe_demandee=ecole['classe'],
                nom='SAWADOGO', prenom='Ali', genre='M', date_naissance=dt.date(2014, 1, 15), lieu_naissance='Kaya',
                parent_nom='SAWADOGO Moussa', parent_telephone='70 12 34 56')
    base.update(extra)
    return PreInscription.objects.create(**base)


class TestPreInscriptions:
    def test_formulaire_cree_la_demande(self, client, ecole):
        html = client.get(reverse('inscriptions:preinscription_create')).content.decode()
        assert 'name="classe_demandee"' in html and 'name="parent_telephone"' in html
        reponse = client.post(reverse('inscriptions:preinscription_create'), {
            'annee_scolaire': ecole['annee'].pk, 'classe_demandee': ecole['classe'].pk, 'nom': 'zongo', 'prenom': 'Fati',
            'genre': 'F', 'date_naissance': '2014-03-03', 'lieu_naissance': 'Ouaga', 'parent_nom': 'ZONGO Paul',
            'parent_telephone': '76 00 00 00',
        })
        assert reponse.status_code == 302
        pre = PreInscription.objects.get(prenom='Fati')
        assert pre.nom == 'ZONGO' and pre.etablissement == ecole['etab'] and pre.statut == PreInscription.Statut.EN_ATTENTE
        # téléphone trop court refusé
        reponse = client.post(reverse('inscriptions:preinscription_create'), {
            'annee_scolaire': ecole['annee'].pk, 'classe_demandee': ecole['classe'].pk, 'nom': 'A', 'prenom': 'B',
            'genre': 'F', 'parent_nom': 'C', 'parent_telephone': '70 12',
        })
        assert reponse.status_code == 200 and PreInscription.objects.count() == 1

    def test_liste_et_synthese(self, client, ecole):
        _demande(ecole)
        _demande(ecole, prenom='Issa', statut=PreInscription.Statut.ACCEPTEE)
        baker.make('inscriptions.Inscription', classe=ecole['classe'], annee_scolaire=ecole['annee'],
                   eleve=baker.make('inscriptions.Eleve', photo=''))
        lignes = synthese_par_classe(ecole['etab'], ecole['annee'])
        ligne = next(l for l in lignes if l['classe'] == ecole['classe'])
        assert (ligne['en_attente'], ligne['acceptees'], ligne['effectif'], ligne['capacite'], ligne['restantes']) == (1, 1, 1, 2, 1)
        html = unescape(client.get(reverse('inscriptions:preinscription_list'), {'annee': ecole['annee'].pk}).content.decode())
        assert 'SAWADOGO Ali' in html and 'SAWADOGO Issa' in html and '6ème A' in html
        html = unescape(client.get(reverse('inscriptions:preinscription_list'),
                                   {'annee': ecole['annee'].pk, 'statut': 'ACCEPTEE'}).content.decode())
        assert 'SAWADOGO Issa' in html and 'SAWADOGO Ali' not in html

    def test_decider(self, client, ecole):
        pre = _demande(ecole)
        reponse = client.post(reverse('inscriptions:preinscription_decider', args=[pre.pk]), {'decision': 'ACCEPTEE'})
        assert reponse.status_code == 302
        pre.refresh_from_db()
        assert pre.statut == PreInscription.Statut.ACCEPTEE and pre.decidee_par == ecole['user'] and pre.decidee_le
        client.post(reverse('inscriptions:preinscription_decider', args=[pre.pk]), {'decision': 'EN_ATTENTE'})
        pre.refresh_from_db()
        assert pre.statut == PreInscription.Statut.EN_ATTENTE and pre.decidee_par is None
        client.post(reverse('inscriptions:preinscription_decider', args=[pre.pk]), {'decision': 'BIDON'})
        pre.refresh_from_db()
        assert pre.statut == PreInscription.Statut.EN_ATTENTE

    def test_inscrire_cree_eleve_et_inscription(self, client, ecole):
        pre = _demande(ecole, statut=PreInscription.Statut.ACCEPTEE)
        reponse = client.post(reverse('inscriptions:preinscription_inscrire', args=[pre.pk]))
        pre.refresh_from_db()
        assert pre.statut == PreInscription.Statut.INSCRITE and pre.inscription_id
        inscription = pre.inscription
        assert reponse.status_code == 302 and reponse.url == reverse('inscriptions:inscription_update', args=[inscription.pk])
        eleve = inscription.eleve
        assert eleve.get_nom_complet() == 'SAWADOGO ALI' and eleve.prenom == 'Ali' and eleve.matricule.startswith('SAV')
        assert eleve.tuteur_nom == 'SAWADOGO Moussa' and eleve.telephone_parent == '70 12 34 56'
        assert inscription.classe == ecole['classe'] and inscription.statut == 'NON_AFFECTE'
        # idempotent : un second clic ne crée rien
        assert inscrire(pre, ecole['user']) == (inscription, None) and Eleve.objects.count() == 1

    def test_inscrire_refuse_classe_complete_date_manquante_et_refusee(self, client, ecole):
        for _ in range(2):
            baker.make('inscriptions.Inscription', classe=ecole['classe'], annee_scolaire=ecole['annee'],
                       eleve=baker.make('inscriptions.Eleve', photo=''))
        pre = _demande(ecole)
        inscription, erreur = inscrire(pre, ecole['user'])
        assert inscription is None and 'complète' in erreur and Inscription.objects.count() == 2
        ecole['classe'].capacite_max = 10
        ecole['classe'].save()
        pre.date_naissance = None
        pre.save()
        assert inscrire(pre, ecole['user'])[1].startswith('Renseignez la date de naissance')
        refusee = _demande(ecole, prenom='Nour', statut=PreInscription.Statut.REFUSEE)
        reponse = client.post(reverse('inscriptions:preinscription_inscrire', args=[refusee.pk]), follow=True)
        refusee.refresh_from_db()
        assert refusee.statut == PreInscription.Statut.REFUSEE and Inscription.objects.count() == 2
        assert 'refusée' in unescape(reponse.content.decode()).lower()

    def test_autre_etablissement_invisible(self, client, ecole):
        autre = baker.make('etablissements.Etablissement')
        pre = _demande(ecole, etablissement=autre)
        assert client.get(reverse('inscriptions:preinscription_update', args=[pre.pk])).status_code == 404
        assert client.post(reverse('inscriptions:preinscription_decider', args=[pre.pk]), {'decision': 'ACCEPTEE'}).status_code == 404
