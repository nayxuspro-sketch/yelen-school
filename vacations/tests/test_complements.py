"""Compléments vacations (5.43.0) : validation des heures, bulletins mensuels, filtres et PDF.

Les parcours déjà couverts (liste des contrats, saisie des heures, liste des bulletins) le sont dans
``test_views.py`` ; ce module couvre les décisions : qui valide, ce qui est généré, ce qui est filtrable.
"""
import datetime as dt
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from vacations.forms import ContratVacationForm
from vacations.models import BulletinVacation, ContratVacation, HeureVacation

pytestmark = pytest.mark.django_db


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def utilisateur(etab):
    return baker.make('accounts.User', etablissement=etab, is_superuser=True, role='SUPER_ADMIN',
                      must_change_password=False)


def _contrat(etab):
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    personnel = baker.make('personnel.MembrePersonnel', etablissement=etab)
    return baker.make('vacations.ContratVacation', personnel=personnel, annee_scolaire=annee,
                      taux_horaire=Decimal('2500'), actif=True)


def test_valider_puis_invalider_une_saisie_d_heures(client, utilisateur):
    contrat = _contrat(utilisateur.etablissement)
    heure = baker.make('vacations.HeureVacation', contrat=contrat, mois=3, annee=2026,
                       heures_effectuees=Decimal('8'), est_valide=False)
    client.force_login(utilisateur)

    reponse = client.post(reverse('vacations:valider_heure', args=[heure.pk]))
    heure.refresh_from_db()
    assert reponse.status_code == 302 and heure.est_valide is True

    client.post(reverse('vacations:invalider_heure', args=[heure.pk]))
    heure.refresh_from_db()
    assert heure.est_valide is False


def test_valider_une_heure_d_un_autre_etablissement_est_refuse(client, utilisateur):
    contrat = _contrat(baker.make('etablissements.Etablissement'))
    heure = baker.make('vacations.HeureVacation', contrat=contrat, est_valide=False)
    client.force_login(utilisateur)
    reponse = client.post(reverse('vacations:valider_heure', args=[heure.pk]))
    heure.refresh_from_db()
    assert reponse.status_code == 404
    assert heure.est_valide is False


def test_liste_des_bulletins_filtrable_par_mois_annee_statut(client, utilisateur):
    contrat = _contrat(utilisateur.etablissement)
    annee = contrat.annee_scolaire
    mars = baker.make('vacations.BulletinVacation', personnel=contrat.personnel, annee_scolaire=annee,
                      mois=3, annee=2026, statut=BulletinVacation.StatutChoices.VALIDE)
    baker.make('vacations.BulletinVacation', personnel=contrat.personnel, annee_scolaire=annee,
               mois=4, annee=2026, statut=BulletinVacation.StatutChoices.BROUILLON)
    client.force_login(utilisateur)

    reponse = client.get(reverse('vacations:bulletin_list'), {'mois': '3', 'annee': '2026', 'statut': 'VALIDE'})
    assert reponse.status_code == 200
    assert list(reponse.context['bulletins']) == [mars]
    assert reponse.context['current_month'] == 3 and reponse.context['current_year'] == 2026


def test_generer_le_bulletin_d_un_mois_calcule_les_totaux(client, utilisateur):
    contrat = _contrat(utilisateur.etablissement)
    baker.make('vacations.HeureVacation', contrat=contrat, mois=3, annee=2026,
               heures_effectuees=Decimal('10'), est_valide=True)
    client.force_login(utilisateur)
    reponse = client.get(reverse('vacations:generer_bulletin', args=[contrat.pk, 3, 2026]))
    bulletin = BulletinVacation.objects.get(personnel=contrat.personnel, mois=3, annee=2026)
    assert reponse.status_code == 302 and bulletin.total_heures == Decimal('10')
    assert bulletin.montant_total == Decimal('25000')


def test_generer_tous_les_bulletins_sans_annee_courante(client, utilisateur):
    annee = baker.make('parametres.AnneeScolaire', etablissement=utilisateur.etablissement, est_courante=False)
    baker.make('vacations.ContratVacation', annee_scolaire=annee, actif=True)
    client.force_login(utilisateur)
    reponse = client.get(reverse('vacations:generer_tous_bulletins'), follow=True)
    assert 'Aucune année scolaire active' in reponse.content.decode()


def test_generer_tous_les_bulletins_du_mois(client, utilisateur):
    contrat = _contrat(utilisateur.etablissement)
    aujourd_hui = dt.date.today()
    baker.make('vacations.HeureVacation', contrat=contrat, mois=aujourd_hui.month, annee=aujourd_hui.year,
               heures_effectuees=Decimal('6'), est_valide=True)
    client.force_login(utilisateur)
    reponse = client.get(reverse('vacations:generer_tous_bulletins'), follow=True)
    assert BulletinVacation.objects.filter(mois=aujourd_hui.month, annee=aujourd_hui.year).count() == 1
    assert '1 bulletin(s) généré(s)' in reponse.content.decode()

    BulletinVacation.objects.all().delete()
    HeureVacation.objects.update(est_valide=False)
    reponse = client.get(reverse('vacations:generer_tous_bulletins'), follow=True)
    assert 'Aucune heure validée' in reponse.content.decode()


def test_valider_un_bulletin_et_refuser_celui_d_un_autre_etablissement(client, utilisateur):
    contrat = _contrat(utilisateur.etablissement)
    bulletin = baker.make('vacations.BulletinVacation', personnel=contrat.personnel,
                          annee_scolaire=contrat.annee_scolaire, statut=BulletinVacation.StatutChoices.BROUILLON)
    client.force_login(utilisateur)
    client.post(reverse('vacations:valider_bulletin', args=[bulletin.pk]))
    bulletin.refresh_from_db()
    assert bulletin.statut == BulletinVacation.StatutChoices.VALIDE

    autre = baker.make('vacations.BulletinVacation', statut=BulletinVacation.StatutChoices.BROUILLON)
    reponse = client.post(reverse('vacations:valider_bulletin', args=[autre.pk]), follow=True)
    autre.refresh_from_db()
    assert autre.statut == BulletinVacation.StatutChoices.BROUILLON
    assert 'Accès refusé' in reponse.content.decode()


def test_bulletin_de_vacation_pdf(client, utilisateur, mocker):
    contrat = _contrat(utilisateur.etablissement)
    bulletin = baker.make('vacations.BulletinVacation', personnel=contrat.personnel,
                          annee_scolaire=contrat.annee_scolaire, mois=3, annee=2026)
    faux_html = mocker.patch('core.pdf.HTML')
    faux_html.return_value.write_pdf.return_value = b'%PDF-1.4 bulletin'
    client.force_login(utilisateur)

    reponse = client.get(reverse('vacations:bulletin_vacation_pdf', args=[bulletin.pk]))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content.startswith(b'%PDF')


def test_creer_un_contrat_par_le_formulaire(client, utilisateur):
    annee = baker.make('parametres.AnneeScolaire', etablissement=utilisateur.etablissement, est_courante=True)
    personnel = baker.make('personnel.MembrePersonnel', etablissement=utilisateur.etablissement)
    client.force_login(utilisateur)
    donnees = {'personnel': personnel.pk, 'annee_scolaire': annee.pk, 'taux_horaire': '3000',
               'heures_hebdo_prevues': '2.5', 'date_debut': '2026-10-01', 'actif': 'on'}

    reponse = client.post(reverse('vacations:contrat_create'), donnees)
    assert reponse.status_code == 302
    contrat = ContratVacation.objects.get(personnel=personnel)
    assert contrat.taux_horaire == Decimal('3000') and contrat.heures_hebdo_prevues == Decimal('2.5')

    incomplete = client.post(reverse('vacations:contrat_create'), {**donnees, 'date_debut': ''})
    assert incomplete.status_code == 200 and incomplete.context['form'].errors['date_debut']


def test_formulaire_de_contrat_prepare_les_listes():
    annee = baker.make('parametres.AnneeScolaire', est_courante=True)
    formule = ContratVacationForm()
    assert list(formule.fields['annee_scolaire'].queryset) == [annee]
    assert formule.fields['enseignement'].required is False
    assert formule.fields['taux_horaire'].initial == 2500
    assert formule.fields['heures_hebdo_prevues'].initial == 2.0
