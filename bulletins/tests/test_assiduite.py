"""Absences et retards du bulletin : relevés dans Présences, corrigeables sur la fiche du conseil de classe."""
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from bulletins.models import Bulletin
from bulletins.services import assiduite_depuis_presences
from presences.models import Presence


@pytest.fixture
def monde(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab,
                                  must_change_password=False))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, nom='4e B')
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
                           date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2026, 12, 20))
    awa, bintou = (baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee,
                              eleve=baker.make('inscriptions.Eleve', nom=nom, prenom='Awa', photo=''))
                   for nom in ('OUEDRAOGO', 'ZONGO'))
    for ins in (awa, bintou):
        baker.make('pedagogie.MoyenneGenerale', inscription=ins, trimestre=trimestre, moyenne=Decimal('12.50'), rang=1)

    def appel(jour, debut=None, fin=None):
        return baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=jour, heure_debut=debut, heure_fin=fin)
    h = datetime.time
    releves = [
        (appel(datetime.date(2026, 10, 5), h(8), h(10)), 'ABSENT'),       # 2 h non justifiées
        (appel(datetime.date(2026, 10, 6), h(10), h(11, 30)), 'ABSENT'),  # 1,5 h → 3,5 h arrondies à 4
        (appel(datetime.date(2026, 11, 2)), 'EXCUSE'),                    # séance sans horaire : 1 h justifiée
        (appel(datetime.date(2026, 11, 3), h(15), h(17)), 'RETARD'),
        (appel(datetime.date(2026, 11, 4), h(7), h(8)), 'RETARD'),
        (appel(datetime.date(2026, 11, 5), h(7), h(8)), 'PRESENT'),
        (appel(datetime.date(2027, 1, 12), h(8), h(12)), 'ABSENT'),       # hors trimestre : ignorée
    ]
    for ap, statut in releves:
        baker.make('presences.Presence', appel=ap, inscription=awa, statut=statut)
        baker.make('presences.Presence', appel=ap, inscription=bintou, statut='PRESENT')
    return {'client': client, 'classe': classe, 'trimestre': trimestre, 'awa': awa, 'bintou': bintou}


@pytest.mark.django_db
def test_releve_des_presences_en_heures_et_retards(monde):
    releve = assiduite_depuis_presences(monde['trimestre'], [monde['awa'], monde['bintou']])
    assert releve == {monde['awa'].pk: {'absences_justifiees': 1, 'absences_non_justifiees': 4, 'retards': 2}}
    assert Presence.objects.filter(inscription=monde['awa']).count() == 7


@pytest.mark.django_db
def test_fiche_et_bulletins_prennent_le_releve_puis_la_correction(monde, mocker):
    from pedagogie.views.bulletins import _build_bulletin_context
    c, awa, bintou, trimestre, classe = (monde[k] for k in ('client', 'awa', 'bintou', 'trimestre', 'classe'))
    # Liste de la classe (aucune fiche) : valeurs relevées
    page = c.get(reverse('bulletins:bulletins_classe', kwargs={'class_id': classe.pk, 'trimestre_id': trimestre.pk}))
    ligne_awa = page.context['lignes'][0]
    assert ligne_awa['inscription'] == awa and ligne_awa['bulletin'] is None
    assert ligne_awa['assiduite'] == {'absences_justifiees': 1, 'absences_non_justifiees': 4, 'retards': 2}
    assert page.context['lignes'][1]['assiduite'] == {'absences_justifiees': 0, 'absences_non_justifiees': 0, 'retards': 0}
    # Aperçu / PDF sans fiche : mêmes valeurs
    mocker.patch('pedagogie.views.bulletins.HTML')
    ctx = _build_bulletin_context(page.wsgi_request, awa, trimestre)
    assert ctx['fiche_bulletin'] is None and ctx['assiduite']['absences_non_justifiees'] == 4
    # Ouverture de la fiche : pré-remplie, corrigeable
    url = reverse('bulletins:bulletin_saisir', kwargs={'inscription_id': awa.pk, 'trimestre_id': trimestre.pk})
    html = c.get(url, HTTP_HX_REQUEST='true').content.decode()
    fiche = Bulletin.objects.get(inscription=awa, trimestre=trimestre)
    assert (fiche.absences_justifiees, fiche.absences_non_justifiees, fiche.retards) == (1, 4, 2)
    assert 'name="absences_non_justifiees" min="0"\n               value="4"' in html
    reponse = c.post(url, {'absences_justifiees': '1', 'absences_non_justifiees': '7', 'retards': '2',
                                  'appreciation_conseil': 'Doit se ressaisir.'}, HTTP_HX_REQUEST='true')
    assert reponse.status_code == 204
    ctx = _build_bulletin_context(page.wsgi_request, awa, trimestre)
    assert ctx['assiduite']['absences_non_justifiees'] == 7, 'la fiche corrigée fait foi'
    # Publication en masse : la fiche de Bintou, créée à cette occasion, part aussi du relevé (ici vierge)
    c.post(reverse('bulletins:bulletins_classe_publier', kwargs={'class_id': classe.pk, 'trimestre_id': trimestre.pk}))
    assert Bulletin.objects.get(inscription=bintou, trimestre=trimestre).est_publie
    assert Bulletin.objects.get(inscription=awa, trimestre=trimestre).absences_non_justifiees == 7
