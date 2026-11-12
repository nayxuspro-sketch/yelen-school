"""Lot G — appréciation par matière : saisie par l'enseignant titulaire (ou la direction), impression sur le bulletin
en lieu et place de la grille des moyennes, conservation au recalcul et verrouillage de la période clôturée."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Resultat
from pedagogie.utils import CalculateurMoyenne

pytestmark = pytest.mark.django_db


@pytest.fixture
def cours(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR', ville='Ouagadougou')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR',
               type_etablissement='PUBLIC')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    t1 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
                    date_debut=date(2026, 10, 1), date_fin=max(date(2026, 12, 20), date.today() + timedelta(days=30)))
    baker.make('parametres.AppreciationMoyenneSecondaire', etablissement=etab, libelle='Bien',
               moy_min=Decimal('0'), moy_max=Decimal('20'), actif=True)
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif',
                      email='salif@ecole.bf')
    maths = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, est_actif=True, personnel=prof,
                       coefficient=Decimal('4'), matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'))
    francais = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, est_actif=True,
                          coefficient=Decimal('3'), matiere=baker.make('pedagogie.Matiere', nom='Français'),
                          personnel=baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZIDA', prenom='Aline'))
    devoir = baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1'), nb_meilleures_notes=0)
    ev = baker.make('pedagogie.Evaluation', enseignement=maths, trimestre=t1, type_evaluation=devoir, titre='Devoir 1',
                    bareme=Decimal('20'), statut='TERMINEE', date_planifiee=date(2026, 11, 5))
    ev_fr = baker.make('pedagogie.Evaluation', enseignement=francais, trimestre=t1, type_evaluation=devoir,
                       titre='Dictée', bareme=Decimal('20'), statut='TERMINEE', date_planifiee=date(2026, 11, 6))

    def inscrire(nom, prenom, statut='ACTIF'):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, photo='')
        return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut=statut)

    awa, eric = inscrire('OUEDRAOGO', 'Awa'), inscrire('KABORE', 'Éric')
    parti = inscrire('TRAORE', 'Désiré', statut='ABANDON')
    baker.make('pedagogie.Note', inscription=awa, evaluation=ev, valeur=Decimal('16'))
    baker.make('pedagogie.Note', inscription=awa, evaluation=ev_fr, valeur=Decimal('12'))
    enseignant = baker.make('accounts.User', etablissement=etab, role='ENSEIGNANT', email='salif@ecole.bf',
                            must_change_password=False)
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', is_superuser=True,
                           must_change_password=False)
    return SimpleNamespace(client=client, etab=etab, annee=annee, classe=classe, t1=t1, maths=maths, francais=francais,
                           awa=awa, eric=eric, parti=parti, enseignant=enseignant, directeur=directeur)


def _url_saisie(c, enseignement):
    return reverse('pedagogie:appreciations_saisir', kwargs={'enseignement_id': enseignement.pk, 'trimestre_id': c.t1.pk})


def test_enseignant_limite_a_ses_disciplines(cours):
    c = cours
    c.client.force_login(c.enseignant)
    index = c.client.get(reverse('pedagogie:appreciations_index'))
    assert [ligne['enseignement'] for ligne in index.context['lignes']] == [c.maths]
    assert index.context['lignes'][0]['effectif'] == 2, 'abandon exclu'

    page = c.client.get(_url_saisie(c, c.maths))
    assert page.status_code == 200
    assert [ligne['inscription'] for ligne in page.context['lignes']] == [c.eric, c.awa]
    assert 'datalist' in page.content.decode()

    refus = c.client.get(_url_saisie(c, c.francais), follow=True)
    assert 'ne vous est pas attribué' in refus.content.decode()
    assert refus.redirect_chain[0][0] == reverse('pedagogie:appreciations_index')


def test_saisie_imprimee_sur_le_bulletin_et_conservee_au_recalcul(cours):
    c = cours
    CalculateurMoyenne.recalculer_classe(c.classe, c.t1)
    c.client.force_login(c.enseignant)
    reponse = c.client.post(_url_saisie(c, c.maths), {
        f'appr_{c.awa.pk}': '  Excellent   trimestre, ' + 'x' * 300,
        f'appr_{c.eric.pk}': 'Aucune note rendue ce trimestre.',
    }, follow=True)
    assert '2 appréciations enregistrées' in reponse.content.decode()
    awa_maths = Resultat.objects.get(inscription=c.awa, enseignement=c.maths, trimestre=c.t1)
    assert awa_maths.appreciation.startswith('Excellent trimestre, x') and len(awa_maths.appreciation) == 200
    assert awa_maths.moyenne == Decimal('16.00'), 'la moyenne calculée est intacte'
    eric_maths = Resultat.objects.get(inscription=c.eric, enseignement=c.maths, trimestre=c.t1)
    assert eric_maths.moyenne is None and eric_maths.coefficient_utilise == Decimal('4')

    # Index : compteur de saisies par période
    index = c.client.get(reverse('pedagogie:appreciations_index'))
    assert index.context['lignes'][0]['periodes'][0]['nb'] == 2

    # Bulletin : l'appréciation saisie remplace la grille pour Maths, la grille reste pour Français
    c.client.force_login(c.directeur)
    apercu = c.client.get(reverse('pedagogie:bulletin_apercu', kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}))
    libelles = {r.enseignement.matiere.nom: r.appreciation.libelle for r in apercu.context['resultats_annotes']}
    assert libelles == {'Mathématiques': awa_maths.appreciation, 'Français': 'Bien'}
    assert 'Excellent trimestre' in apercu.content.decode()

    # Recalcul : l'appréciation survit, y compris pour l'élève sans note (ligne conservée sans moyenne)
    CalculateurMoyenne.recalculer_classe(c.classe, c.t1)
    assert Resultat.objects.get(pk=awa_maths.pk).appreciation == awa_maths.appreciation
    eric_maths.refresh_from_db()
    assert (eric_maths.appreciation, eric_maths.moyenne, eric_maths.nb_notes) == ('Aucune note rendue ce trimestre.', None, 0)
    assert not Resultat.objects.filter(inscription=c.eric, enseignement=c.francais).exists(), 'sans note ni appréciation : supprimé'

    # Effacer une appréciation rend la main à la grille
    c.client.force_login(c.enseignant)
    c.client.post(_url_saisie(c, c.maths), {f'appr_{c.awa.pk}': '', f'appr_{c.eric.pk}': 'Aucune note rendue ce trimestre.'})
    c.client.force_login(c.directeur)
    apercu = c.client.get(reverse('pedagogie:bulletin_apercu', kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}))
    assert {r.appreciation.libelle for r in apercu.context['resultats_annotes']} == {'Bien'}


def test_periode_cloturee_refuse_la_saisie(cours):
    c = cours
    c.t1.cloturer(ouvert=False)
    c.client.force_login(c.directeur)
    page = c.client.get(_url_saisie(c, c.maths))
    assert 'readonly' in page.content.decode() and 'Période clôturée' in page.content.decode()
    reponse = c.client.post(_url_saisie(c, c.maths), {f'appr_{c.awa.pk}': 'Trop tard'}, follow=True)
    assert 'est clôturé' in reponse.content.decode()
    assert not Resultat.objects.filter(inscription=c.awa).exists()
