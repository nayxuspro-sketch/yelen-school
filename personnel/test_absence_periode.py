"""Absences du personnel : impression d'une période (intervalle de dates) et modalité « Toutes les matières »."""
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    prim = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire', ordre=1)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=prim, nom='CP1', niveau='CP1')
    maitre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif',
                        fonction='Enseignant')
    autre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Paul',
                       fonction='Professeur')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False, est_tous_cycles=True)
    baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
               date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    client.force_login(user)
    return {'etab': etab, 'prim': prim, 'classe': classe, 'maitre': maitre, 'autre': autre, 'user': user,
            'client': client}


def _absence(membre, debut, fin=None, **extra):
    return baker.make('personnel.AbsencePersonnel', personnel=membre, date_debut=debut, date_fin=fin or debut,
                      observation='Raison de santé', **extra)


def _lignes(reponse):
    """Absences listées dans la liste (attribut de contexte) pour les bornes demandées."""
    return list(reponse.context['absences'])


def test_la_liste_accepte_un_intervalle_de_dates(ecole):
    dedans = _absence(ecole['maitre'], date(2026, 10, 5))
    chevauche = _absence(ecole['autre'], date(2026, 10, 1), date(2026, 10, 9))
    _absence(ecole['maitre'], date(2026, 9, 20))                     # avant la période
    _absence(ecole['maitre'], date(2026, 11, 3))                     # après la période
    page = ecole['client'].get(reverse('personnel:absence_list'), {'du': '2026-10-04', 'au': '2026-10-06'})
    assert page.status_code == 200
    assert {a.pk for a in _lignes(page)} == {dedans.pk, chevauche.pk}
    assert page.context['periode'] == {'debut': date(2026, 10, 4), 'fin': date(2026, 10, 6),
                                       'du': '2026-10-04', 'au': '2026-10-06'}
    jours = {l['membre']: l['jours'] for l in page.context['bilan']}
    assert jours == {ecole['maitre']: 1, ecole['autre']: 3}, 'jours bornés à la période'


def test_les_bornes_inversees_sont_remises_dans_l_ordre(ecole):
    absence = _absence(ecole['maitre'], date(2026, 10, 5))
    page = ecole['client'].get(reverse('personnel:absence_list'), {'du': '2026-10-06', 'au': '2026-10-04'})
    assert page.context['periode']['debut'] == date(2026, 10, 4)
    assert page.context['periode']['fin'] == date(2026, 10, 6)
    assert [a.pk for a in _lignes(page)] == [absence.pk]
    assert ecole['client'].get(reverse('personnel:absence_list'), {'du': 'illisible'}).status_code == 200


def test_impression_de_la_periode_en_pdf(ecole, mocker):
    _absence(ecole['maitre'], date(2026, 10, 5), toutes_matieres=True)
    _absence(ecole['autre'], date(2026, 11, 3))             # hors période
    html_cls = mocker.patch('core.pdf.HTML')
    html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 absences'
    url = reverse('personnel:absence_pdf')
    reponse = ecole['client'].get(url, {'du': '2026-10-01', 'au': '2026-10-31'})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert 'absences_20261001_20261031.pdf' in reponse['Content-Disposition']

    html = html_cls.call_args.kwargs['string']
    assert 'Absences du personnel' in html and '01/10/2026 au 31/10/2026' in html
    assert 'KABORE Salif' in html and 'Toutes les matières' in html
    assert 'ZONGO Paul' not in html, 'absence hors période non imprimée'
    assert 'Bilan par agent' in html and 'Document établi le' in html


def test_le_lien_d_impression_conserve_la_periode(ecole):
    page = ecole['client'].get(reverse('personnel:absence_list'), {'du': '2026-10-01', 'au': '2026-10-31'})
    lien = page.context['lien_impression']
    assert lien.startswith(reverse('personnel:absence_pdf'))
    assert 'du=2026-10-01' in lien and 'au=2026-10-31' in lien and 'format=pdf' in lien
    assert 'Imprimer la période' in page.content.decode()


def test_toutes_les_matieres_au_primaire(ecole):
    from personnel.forms import AbsencePersonnelForm
    matiere = baker.make('pedagogie.Matiere', code='MATH', nom='Mathématiques')
    donnees = {'personnel': ecole['maitre'].pk, 'date': '2026-11-04', 'classe': ecole['classe'].pk,
               'matiere': matiere.pk, 'toutes_matieres': 'on', 'heure_debut': '08:00', 'heure_fin': '10:00',
               'observation': 'Raison de santé'}
    form = AbsencePersonnelForm(donnees, etablissement=ecole['etab'])
    assert form.is_valid(), form.errors
    absence = form.save()
    assert absence.toutes_matieres is True and absence.matiere is None, 'aucune matière retenue'
    assert absence.matiere_libelle == 'Toutes les matières'

    page = ecole['client'].get(reverse('personnel:absence_list'), {'du': '2026-11-01', 'au': '2026-11-30'})
    assert 'Toutes les matières' in page.content.decode()
    assert 'name="toutes_matieres"' in ecole['client'].get(reverse('personnel:absence_create')).content.decode()
