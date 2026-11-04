"""Lot 5 (5.51.0) — pointage du personnel (journée, feuille mensuelle, PDF signé) et entretien annuel
d'évaluation (grille de 5 critères notés 0 à 5, bilan, objectifs, avis, PDF signé)."""
from datetime import date, time

import pytest
from django.urls import reverse
from model_bakery import baker

from personnel.models import EvaluationAnnuelle, PointagePersonnel, ReglagePointage

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    autre = baker.make('etablissements.Etablissement', nom='AUTRE')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    agent = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif',
                       fonction='Enseignant', matricule='AG-001', is_active=True, photo='', signature='')
    chef = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Awa',
                      fonction='Directrice', is_active=True, photo='', signature='')
    etranger = baker.make('personnel.MembrePersonnel', etablissement=autre, nom='AILLEURS', prenom='Paul',
                          is_active=True, photo='', signature='')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'annee': annee, 'agent': agent, 'chef': chef, 'etranger': etranger, 'client': client}


# ── Modèles ──────────────────────────────────────────────────────────────────

def test_statut_deduit_de_l_heure_d_arrivee(ecole):
    limite = ReglagePointage.HEURE_PAR_DEFAUT
    assert limite == time(7, 30)
    assert PointagePersonnel.statut_depuis(time(7, 30), limite) == PointagePersonnel.StatutChoices.PRESENT
    assert PointagePersonnel.statut_depuis(time(7, 31), limite) == PointagePersonnel.StatutChoices.RETARD
    assert PointagePersonnel.statut_depuis(None, limite) == PointagePersonnel.StatutChoices.ABSENT


def test_heures_travaillees_et_reglage_par_etablissement(ecole):
    p = PointagePersonnel(personnel=ecole['agent'], date=date(2026, 11, 2),
                          heure_arrivee=time(7, 15), heure_depart=time(12, 45))
    assert p.heures_travaillees == 5.5
    assert PointagePersonnel(personnel=ecole['agent'], date=date(2026, 11, 3),
                             heure_arrivee=time(7, 15)).heures_travaillees == 0.0
    reglage = ReglagePointage.pour(ecole['etab'])
    assert reglage.pk == ReglagePointage.pour(ecole['etab']).pk          # une seule ligne par établissement
    assert reglage.heure_arrivee_limite == time(7, 30)


def test_moyenne_de_l_evaluation_sur_20(ecole):
    e = EvaluationAnnuelle(personnel=ecole['agent'], annee_scolaire=ecole['annee'],
                           date_entretien=date(2026, 11, 4), evaluateur=ecole['chef'])
    assert (e.ponctualite, e.competence, e.qualite, e.relations, e.initiative) == (3, 3, 3, 3, 3)
    assert e.total_points == 15 and e.moyenne_sur_20 == 12.0
    e.ponctualite = 5
    assert e.total_points == 17 and e.moyenne_sur_20 == 13.6
    assert [libelle for libelle, _note in e.notes][0] == 'Ponctualité et assiduité'


# ── Pointage ─────────────────────────────────────────────────────────────────

def test_pointage_du_jour_enregistre_les_lignes_renseignees(ecole):
    url = reverse('personnel:pointage_jour')
    page = ecole['client'].get(url)
    assert page.status_code == 200
    assert 'KABORE' in page.content.decode()
    assert 'AILLEURS' not in page.content.decode()                      # isolation établissement

    reponse = ecole['client'].post(url, {
        'date': '2026-11-04',
        f'arrivee_{ecole["agent"].pk}': '07:15', f'depart_{ecole["agent"].pk}': '12:30',
        f'statut_{ecole["agent"].pk}': '', f'observation_{ecole["agent"].pk}': '',
        f'arrivee_{ecole["chef"].pk}': '08:05', f'depart_{ecole["chef"].pk}': '',
        f'statut_{ecole["chef"].pk}': '', f'observation_{ecole["chef"].pk}': 'Retard signalé',
    })
    assert reponse.status_code == 302
    a = PointagePersonnel.objects.get(personnel=ecole['agent'], date=date(2026, 11, 4))
    c = PointagePersonnel.objects.get(personnel=ecole['chef'], date=date(2026, 11, 4))
    assert a.statut == PointagePersonnel.StatutChoices.PRESENT and a.heures_travaillees == 5.25
    assert c.statut == PointagePersonnel.StatutChoices.RETARD and c.observation == 'Retard signalé'


def test_pointage_du_jour_ignore_les_lignes_vides_et_respecte_le_statut_choisi(ecole):
    url = reverse('personnel:pointage_jour')
    ecole['client'].post(url, {'date': '2026-11-05'})
    assert not PointagePersonnel.objects.filter(date=date(2026, 11, 5)).exists()

    ecole['client'].post(url, {
        'date': '2026-11-05',
        f'arrivee_{ecole["agent"].pk}': '', f'depart_{ecole["agent"].pk}': '',
        f'statut_{ecole["agent"].pk}': 'CONGE', f'observation_{ecole["agent"].pk}': 'Congé maternité',
    })
    p = PointagePersonnel.objects.get(personnel=ecole['agent'], date=date(2026, 11, 5))
    assert p.statut == PointagePersonnel.StatutChoices.CONGE and p.heure_arrivee is None


def test_heure_limite_enregistree_depuis_le_pointage_du_jour(ecole):
    url = reverse('personnel:pointage_jour')
    ecole['client'].post(url, {'date': '2026-11-04', 'action': 'limite', 'heure_arrivee_limite': '08:00'})
    assert ReglagePointage.pour(ecole['etab']).heure_arrivee_limite == time(8, 0)

    ecole['client'].post(url, {'date': '2026-11-04', 'action': 'limite', 'heure_arrivee_limite': 'xx'})
    assert ReglagePointage.pour(ecole['etab']).heure_arrivee_limite == time(8, 0)   # valeur illisible ignorée


def test_feuille_de_pointage_du_mois_agrege_et_son_pdf(ecole):
    from personnel.views import pointage_mois_pdf

    agent = ecole['agent']
    baker.make(PointagePersonnel, personnel=agent, date=date(2026, 11, 2), heure_arrivee=time(7, 10),
               heure_depart=time(12, 10), statut=PointagePersonnel.StatutChoices.PRESENT)
    baker.make(PointagePersonnel, personnel=agent, date=date(2026, 11, 3), heure_arrivee=time(8, 0),
               heure_depart=time(12, 0), statut=PointagePersonnel.StatutChoices.RETARD)
    baker.make(PointagePersonnel, personnel=agent, date=date(2026, 11, 4),
               statut=PointagePersonnel.StatutChoices.ABSENT)

    page = ecole['client'].get(reverse('personnel:pointage_mois'), {'mois': 11, 'annee': 2026})
    assert page.status_code == 200
    html = page.content.decode()
    lignes = page.context['lignes']
    assert lignes[0]['jours'] == 3 and lignes[0]['retards'] == 1 and lignes[0]['absences'] == 1
    assert lignes[0]['heures'] == 9.0                     # 5 h + 4 h
    assert page.context['totaux']['jours'] == 3
    assert 'Retards' in html

    reponse = ecole['client'].get(reverse('personnel:pointage_mois_pdf'), {'mois': 11, 'annee': 2026})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content[:4] == b'%PDF'
    assert pointage_mois_pdf is not None


# ── Horaires individuels et par profil (5.53.0) ─────────────────────────────

def test_heures_de_reference_par_profil_et_par_agent(ecole):
    reglage = ReglagePointage.pour(ecole['etab'])
    # Sans réglage de profil : tout le monde suit la limite de l'établissement.
    assert ecole['agent'].heure_limite_pointage(reglage) == time(7, 30)
    assert ecole['agent'].heure_depart_pointage(reglage) is None

    reglage.heure_arrivee_limite_enseignant = time(9, 0)
    reglage.heure_depart_normale_enseignant = time(11, 0)
    reglage.heure_depart_normale_administration = time(16, 30)
    reglage.save()

    enseignant = baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='OUEDRAOGO',
                            prenom='Awa', fonction='Enseignant', photo='', signature='')
    assert enseignant.profil_pointage == 'ENSEIGNANT'                     # déduit du titre
    assert ecole['chef'].profil_pointage == 'ADMINISTRATION'
    assert enseignant.heure_limite_pointage(reglage) == time(9, 0)        # profil enseignant
    assert ecole['chef'].heure_limite_pointage(reglage) == time(7, 30)    # profil administration → établissement
    assert enseignant.heure_depart_pointage(reglage) == time(11, 0)
    assert ecole['chef'].heure_depart_pointage(reglage) == time(16, 30)

    enseignant.heure_arrivee_limite = time(9, 15)                         # l'horaire de l'agent prime
    enseignant.heure_depart_normale = time(12, 0)
    enseignant.save()
    assert enseignant.heure_limite_pointage(reglage) == time(9, 15)
    assert enseignant.heure_depart_pointage(reglage) == time(12, 0)


def test_horaires_de_reference_enregistres_depuis_le_pointage(ecole):
    url = reverse('personnel:pointage_jour')
    ecole['client'].post(url, {'date': '2026-11-04', 'action': 'horaires',
                               'heure_arrivee_limite': '07:45',
                               'heure_arrivee_limite_enseignant': '09:00',
                               'heure_arrivee_limite_administration': '',
                               'heure_depart_normale': '16:00',
                               'heure_depart_normale_enseignant': '11:00',
                               'heure_depart_normale_administration': ''})
    reglage = ReglagePointage.pour(ecole['etab'])
    assert reglage.heure_arrivee_limite == time(7, 45)
    assert reglage.heure_arrivee_limite_enseignant == time(9, 0)
    assert reglage.heure_arrivee_limite_administration is None            # vide = héritage
    assert reglage.heure_depart_normale_enseignant == time(11, 0)
    assert reglage.depart_pour('ADMINISTRATION') == time(16, 0)           # hérite de l'établissement

    ecole['client'].post(url, {'date': '2026-11-04', 'action': 'horaires', 'heure_arrivee_limite': 'xx'})
    assert ReglagePointage.pour(ecole['etab']).heure_arrivee_limite == time(7, 45)   # illisible : ignoré


def test_horaires_individuels_d_un_agent_enregistres(ecole):
    url = reverse('personnel:pointage_jour')
    agent = ecole['agent']
    ecole['client'].post(url, {'date': '2026-11-04', 'action': 'horaires_agents',
                               f'limite_{agent.pk}': '09:00', f'depart_prevu_{agent.pk}': '11:00'})
    agent.refresh_from_db()
    assert (agent.heure_arrivee_limite, agent.heure_depart_normale) == (time(9, 0), time(11, 0))

    ecole['client'].post(url, {'date': '2026-11-04', 'action': 'horaires_agents',
                               f'limite_{agent.pk}': '', f'depart_prevu_{agent.pk}': ''})
    agent.refresh_from_db()
    assert (agent.heure_arrivee_limite, agent.heure_depart_normale) == (None, None)   # retour au profil


def test_statut_calcule_sur_la_limite_propre_de_l_enseignant(ecole):
    url = reverse('personnel:pointage_jour')
    reglage = ReglagePointage.pour(ecole['etab'])
    reglage.heure_arrivee_limite_enseignant = time(9, 0)
    reglage.heure_depart_normale_enseignant = time(11, 0)
    reglage.save()
    agent = ecole['agent']

    # 8h05 : en retard pour l'administration (limite 7h30), à l'heure pour un enseignant (limite 9h00).
    ecole['client'].post(url, {'date': '2026-11-04',
                               f'arrivee_{agent.pk}': '08:05', f'depart_{agent.pk}': '10:30',
                               f'statut_{agent.pk}': '', f'observation_{agent.pk}': ''})
    p = PointagePersonnel.objects.get(personnel=agent, date=date(2026, 11, 4))
    assert p.statut == PointagePersonnel.StatutChoices.PRESENT
    assert p.est_depart_anticipe(p.personnel.heure_depart_pointage(reglage))            # parti avant 11h00

    ecole['client'].post(url, {'date': '2026-11-05',
                               f'arrivee_{agent.pk}': '09:10', f'depart_{agent.pk}': '11:05',
                               f'statut_{agent.pk}': '', f'observation_{agent.pk}': ''})
    p = PointagePersonnel.objects.get(personnel=agent, date=date(2026, 11, 5))
    assert p.statut == PointagePersonnel.StatutChoices.RETARD
    assert not p.est_depart_anticipe(p.personnel.heure_depart_pointage(reglage))


def test_feuille_du_mois_compte_les_departs_anticipes(ecole):
    reglage = ReglagePointage.pour(ecole['etab'])
    reglage.heure_depart_normale = time(16, 0)
    reglage.save()
    agent = ecole['agent']
    baker.make(PointagePersonnel, personnel=agent, date=date(2026, 11, 2), heure_arrivee=time(7, 10),
               heure_depart=time(15, 0), statut=PointagePersonnel.StatutChoices.PRESENT)
    baker.make(PointagePersonnel, personnel=agent, date=date(2026, 11, 3), heure_arrivee=time(7, 10),
               heure_depart=time(16, 5), statut=PointagePersonnel.StatutChoices.PRESENT)

    page = ecole['client'].get(reverse('personnel:pointage_mois'), {'mois': 11, 'annee': 2026})
    ligne = page.context['lignes'][0]
    assert ligne['departs_anticipes'] == 1 and page.context['totaux']['departs_anticipes'] == 1
    assert 'Départs anticipés' in page.content.decode()


# ── Deux plages par jour : matin et après-midi (5.54.0) ─────────────────────

def test_deux_plages_somment_les_heures_du_jour(ecole):
    # Enseignant : cours de 9h00 à 11h00 puis de 15h00 à 17h00 → 4 h travaillées, pas 8 h.
    p = PointagePersonnel(personnel=ecole['agent'], date=date(2026, 11, 6),
                          heure_arrivee=time(8, 55), heure_depart=time(11, 0),
                          heure_arrivee_apres_midi=time(15, 0), heure_depart_apres_midi=time(17, 5))
    assert p.heures_matin == 2.08 and p.heures_apres_midi == 2.08          # 8h55→11h00, 15h00→17h05
    assert p.heures_travaillees == 4.16
    assert p.heure_arrivee_effective == time(8, 55)                 # première arrivée
    assert p.heure_depart_effective == time(17, 5)                  # dernier départ

    # Plage de l'après-midi incomplète : elle ne compte pas, le matin reste acquis.
    p.heure_depart_apres_midi = None
    assert p.heures_apres_midi == 0.0 and p.heures_travaillees == 2.08
    assert p.heure_depart_effective == time(11, 0)


def test_plages_saisies_et_enregistrees_depuis_le_pointage_du_jour(ecole):
    url = reverse('personnel:pointage_jour')
    agent = ecole['agent']
    reglage = ReglagePointage.pour(ecole['etab'])
    reglage.heure_arrivee_limite_enseignant = time(9, 0)                 # horaire propre au profil enseignant
    reglage.save()
    page = ecole['client'].get(url, {'date': '2026-11-06'})
    assert page.status_code == 200
    html = page.content.decode()
    assert f'name="arrivee_pm_{agent.pk}"' in html and f'name="depart_pm_{agent.pk}"' in html
    assert 'Après-midi' in html and 'Matin' in html

    ecole['client'].post(url, {'date': '2026-11-06',
                               f'arrivee_{agent.pk}': '08:55', f'depart_{agent.pk}': '11:00',
                               f'arrivee_pm_{agent.pk}': '15:00', f'depart_pm_{agent.pk}': '17:05',
                               f'statut_{agent.pk}': '', f'observation_{agent.pk}': ''})
    p = PointagePersonnel.objects.get(personnel=agent, date=date(2026, 11, 6))
    assert (p.heure_arrivee, p.heure_depart) == (time(8, 55), time(11, 0))
    assert (p.heure_arrivee_apres_midi, p.heure_depart_apres_midi) == (time(15, 0), time(17, 5))
    assert p.heures_travaillees == 4.16 and p.statut == PointagePersonnel.StatutChoices.PRESENT


def test_absence_de_plage_l_apres_midi_n_est_pas_une_absence(ecole):
    url = reverse('personnel:pointage_jour')
    agent = ecole['agent']
    reglage = ReglagePointage.pour(ecole['etab'])
    reglage.heure_arrivee_limite_enseignant = time(9, 0)
    reglage.save()
    # Enseignant sans cours l'après-midi : seule la plage du matin est renseignée.
    ecole['client'].post(url, {'date': '2026-11-09',
                               f'arrivee_{agent.pk}': '08:50', f'depart_{agent.pk}': '11:00',
                               f'arrivee_pm_{agent.pk}': '', f'depart_pm_{agent.pk}': '',
                               f'statut_{agent.pk}': '', f'observation_{agent.pk}': ''})
    p = PointagePersonnel.objects.get(personnel=agent, date=date(2026, 11, 9))
    assert p.statut == PointagePersonnel.StatutChoices.PRESENT
    assert p.heures_travaillees == 2.17 and p.heure_arrivee_apres_midi is None


def test_retard_apprecie_sur_la_premiere_arrivee_et_depart_anticipe_sur_le_dernier(ecole):
    reglage = ReglagePointage.pour(ecole['etab'])
    reglage.heure_depart_normale = time(17, 0)
    reglage.save()
    agent = ecole['agent']

    # Arrivée de l'après-midi seule, après 07:30 : c'est elle qui fixe le statut.
    p = PointagePersonnel(personnel=agent, date=date(2026, 11, 10),
                          heure_arrivee_apres_midi=time(15, 0), heure_depart_apres_midi=time(18, 0))
    assert PointagePersonnel.statut_depuis(p.heure_arrivee_effective,
                                          agent.heure_limite_pointage(reglage)) == PointagePersonnel.StatutChoices.RETARD
    assert not p.est_depart_anticipe(reglage.heure_depart_normale)          # parti à 18h00, après 17h00

    # Le départ anticipé se juge sur le dernier départ de la journée.
    p = PointagePersonnel(personnel=agent, date=date(2026, 11, 11),
                          heure_arrivee=time(7, 0), heure_depart=time(11, 0),
                          heure_arrivee_apres_midi=time(15, 0), heure_depart_apres_midi=time(16, 0))
    assert p.est_depart_anticipe(reglage.heure_depart_normale)


def test_feuille_du_mois_additionne_les_deux_plages(ecole):
    agent = ecole['agent']
    baker.make(PointagePersonnel, personnel=agent, date=date(2026, 11, 2),
               heure_arrivee=time(9, 0), heure_depart=time(11, 0),
               heure_arrivee_apres_midi=time(15, 0), heure_depart_apres_midi=time(17, 0),
               statut=PointagePersonnel.StatutChoices.PRESENT)
    page = ecole['client'].get(reverse('personnel:pointage_mois'), {'mois': 11, 'annee': 2026})
    assert page.context['lignes'][0]['heures'] == 4.0


# ── Évaluation annuelle ──────────────────────────────────────────────────────

def test_liste_des_evaluations_et_agents_restant_a_evaluer(ecole):
    baker.make(EvaluationAnnuelle, personnel=ecole['agent'], annee_scolaire=ecole['annee'],
               date_entretien=date(2026, 11, 3), evaluateur=ecole['chef'])
    page = ecole['client'].get(reverse('personnel:evaluation_list'))
    assert page.status_code == 200
    assert [e.personnel for e in page.context['evaluations']] == [ecole['agent']]
    assert ecole['chef'] in page.context['a_evaluer']
    assert ecole['agent'] not in page.context['a_evaluer']


def test_saisie_complete_d_un_entretien_annuel(ecole):
    url = reverse('personnel:evaluation_create')
    assert ecole['client'].get(url).status_code == 200

    reponse = ecole['client'].post(url, {
        'personnel': ecole['agent'].pk, 'annee_scolaire': ecole['annee'].pk,
        'date_entretien': '2026-11-04', 'evaluateur': ecole['chef'].pk,
        'ponctualite': 5, 'competence': 4, 'qualite': 4, 'relations': 5, 'initiative': 3,
        'bilan': 'Année satisfaisante.', 'objectifs': 'Renforcer le suivi des élèves.', 'avis': 'FAVORABLE',
    })
    assert reponse.status_code == 302
    e = EvaluationAnnuelle.objects.get(personnel=ecole['agent'], annee_scolaire=ecole['annee'])
    assert e.total_points == 21 and e.moyenne_sur_20 == 16.8
    assert e.evaluateur == ecole['chef'] and e.avis == EvaluationAnnuelle.AvisChoices.FAVORABLE


def test_evaluation_notes_hors_bornes_et_doublon_refuses(ecole):
    url = reverse('personnel:evaluation_create')
    base = {'personnel': ecole['agent'].pk, 'annee_scolaire': ecole['annee'].pk, 'date_entretien': '2026-11-04',
            'evaluateur': '', 'bilan': '', 'objectifs': '', 'avis': 'RESERVE',
            'ponctualite': 4, 'competence': 4, 'qualite': 4, 'relations': 4, 'initiative': 4}

    page = ecole['client'].post(url, {**base, 'ponctualite': 7})
    assert page.status_code == 200 and 'entre 0 et 5' in page.content.decode()
    assert not EvaluationAnnuelle.objects.exists()

    ecole['client'].post(url, base)
    assert EvaluationAnnuelle.objects.count() == 1
    page = ecole['client'].post(url, {**base, 'competence': 5})
    assert page.status_code == 200
    assert 'a déjà une évaluation' in page.content.decode()
    assert EvaluationAnnuelle.objects.count() == 1


def test_pdf_et_suppression_d_une_evaluation(ecole):
    e = baker.make(EvaluationAnnuelle, personnel=ecole['agent'], annee_scolaire=ecole['annee'],
                   date_entretien=date(2026, 11, 3), evaluateur=ecole['chef'], avis='RESERVE')

    page = ecole['client'].get(reverse('personnel:evaluation_pdf', args=[e.pk]))
    assert page.status_code == 200 and page.content[:4] == b'%PDF'

    assert ecole['client'].get(reverse('personnel:evaluation_delete', args=[e.pk])).status_code == 405
    assert ecole['client'].post(reverse('personnel:evaluation_delete', args=[e.pk])).status_code == 302
    assert not EvaluationAnnuelle.objects.filter(pk=e.pk).exists()


def test_evaluation_d_un_agent_d_un_autre_etablissement_inaccessible(ecole):
    e = baker.make(EvaluationAnnuelle, personnel=ecole['etranger'], annee_scolaire=ecole['annee'],
                   date_entretien=date(2026, 11, 3))
    assert ecole['client'].get(reverse('personnel:evaluation_pdf', args=[e.pk])).status_code == 404
    assert ecole['client'].post(reverse('personnel:evaluation_delete', args=[e.pk])).status_code == 404
