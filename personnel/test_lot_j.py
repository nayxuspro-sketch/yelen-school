"""Lot J — absences du personnel (saisie, bilan mensuel, retenue proposée sur la paie) et attestation de travail."""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from personnel import paie
from personnel.models import AbsencePersonnel

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    autre = baker.make('etablissements.Etablissement', nom='AUTRE')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    agent = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif', fonction='Enseignant',
                       titre_capacite='CAP-CEG', date_embauche=date(2018, 10, 1), est_vacataire=False, est_contractuel=True,
                       is_active=True, photo='', signature='')
    etranger = baker.make('personnel.MembrePersonnel', etablissement=autre, nom='AILLEURS', prenom='Paul', is_active=True,
                          photo='', signature='')
    baker.make('personnel.SalairePersonnel', personnel=agent, annee_scolaire=annee, mois=9, annee=2026,
               salaire_base=Decimal('150000'), retenue_cnss=Decimal('0'), retenue_iuts=Decimal('0'), statut='PAYE')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'annee': annee, 'agent': agent, 'etranger': etranger, 'user': user, 'client': client}


def _absence(agent, debut, fin, **extra):
    return baker.make(AbsencePersonnel, personnel=agent, date_debut=debut, date_fin=fin, **{'motif': 'NON_JUSTIFIEE', **extra})


# ── Modèle ───────────────────────────────────────────────────────────────────

def test_nombre_de_jours_et_regle_de_retenue(ecole):
    a = _absence(ecole['agent'], date(2026, 10, 5), date(2026, 10, 7))
    assert a.nombre_jours == 3 and a.a_retenir, 'non justifiée et retenue cochée → retenue proposée'
    assert not _absence(ecole['agent'], date(2026, 10, 8), date(2026, 10, 8), motif='MALADIE', justifiee=True).a_retenir
    assert not _absence(ecole['agent'], date(2026, 10, 9), date(2026, 10, 9), retenue=False).a_retenir


def test_les_jours_retenus_sont_bornes_au_mois_civil(ecole):
    agent = ecole['agent']
    _absence(agent, date(2026, 9, 29), date(2026, 10, 2))                      # 2 jours en octobre (1er et 2)
    _absence(agent, date(2026, 10, 15), date(2026, 10, 15))                    # 1 jour
    _absence(agent, date(2026, 10, 20), date(2026, 10, 21), justifiee=True)    # justifiée : ignorée
    _absence(agent, date(2026, 10, 30), date(2026, 11, 3), retenue=False)      # sans retenue : ignorée
    assert AbsencePersonnel.jours_retenus(agent, 10, 2026) == 3
    assert AbsencePersonnel.jours_retenus(agent, 9, 2026) == 2
    assert AbsencePersonnel.jours_retenus(agent, 11, 2026) == 0


# ── Paie ─────────────────────────────────────────────────────────────────────

def test_la_preparation_de_la_paie_propose_la_retenue_des_absences(ecole):
    e = ecole
    _absence(e['agent'], date(2026, 10, 5), date(2026, 10, 7))
    _absence(e['agent'], date(2026, 10, 12), date(2026, 10, 12), motif='MALADIE', justifiee=True)
    crees, _ = paie.preparer(e['etab'], 10, 2026, e['annee'], e['user'])
    bulletin = crees[0]
    assert bulletin.autres_retenues == Decimal('15000'), '150 000 / 30 × 3 jours'
    assert 'Retenue absences : 3 jour(s) non justifié(s)' in bulletin.observations
    assert bulletin.salaire_net == bulletin.salaire_brut - Decimal('15000')


def test_sans_absence_aucune_retenue_n_est_proposee(ecole):
    e = ecole
    crees, _ = paie.preparer(e['etab'], 10, 2026, e['annee'], e['user'])
    assert crees[0].autres_retenues == 0 and 'Retenue absences' not in crees[0].observations


def test_la_retenue_est_arrondie_au_franc(ecole):
    e = ecole
    baker.make('personnel.SalairePersonnel', personnel=e['agent'], annee_scolaire=e['annee'], mois=11, annee=2026,
               salaire_base=Decimal('100000'), statut='PAYE')
    _absence(e['agent'], date(2026, 12, 1), date(2026, 12, 1))
    crees, _ = paie.preparer(e['etab'], 12, 2026, e['annee'], e['user'])
    assert crees[0].autres_retenues == Decimal('3333')


# ── Écrans ───────────────────────────────────────────────────────────────────

def test_saisie_d_une_absence_depuis_la_liste(ecole):
    c = ecole['client']
    reponse = c.get(reverse('personnel:absence_create'))
    assert reponse.status_code == 200
    assert list(reponse.context['form'].fields['personnel'].queryset) == [ecole['agent']], 'agents de l\'établissement seulement'
    reponse = c.post(reverse('personnel:absence_create'), {
        'personnel': str(ecole['agent'].pk), 'date_debut': '2026-10-05', 'date_fin': '2026-10-06',
        'motif': 'PERMISSION', 'retenue': 'on', 'observation': 'Décès dans la famille',
    }, follow=True)
    assert reponse.redirect_chain[-1][0] == reverse('personnel:absence_list')
    absence = AbsencePersonnel.objects.get()
    assert (absence.motif, absence.justifiee, absence.retenue, absence.created_by) == ('PERMISSION', False, True, ecole['user'])
    assert 'enregistrée (2 jour(s), retenue proposée sur la paie)' in reponse.content.decode()


def test_saisie_depuis_la_fiche_de_l_agent_et_dates_incoherentes(ecole):
    c = ecole['client']
    url = reverse('personnel:absence_create_pour', args=[ecole['agent'].pk])
    reponse = c.get(url)
    assert reponse.status_code == 200 and reponse.context['form'].initial['personnel'] == ecole['agent']
    reponse = c.post(url, {'personnel': str(ecole['agent'].pk), 'date_debut': '2026-10-06', 'date_fin': '2026-10-05',
                           'motif': 'MALADIE', 'justifiee': 'on'})
    assert reponse.status_code == 200 and 'postérieure ou égale' in reponse.context['form'].errors['date_fin'][0]
    reponse = c.post(url, {'personnel': str(ecole['agent'].pk), 'date_debut': '2026-10-05', 'date_fin': '2026-10-05',
                           'motif': 'MALADIE', 'justifiee': 'on', 'retenue': 'on'})
    assert reponse.status_code == 302 and reponse.url == reverse('personnel:detail', args=[ecole['agent'].pk])
    assert not AbsencePersonnel.objects.get().a_retenir, 'justifiée : pas de retenue même si la case est cochée'
    assert c.get(reverse('personnel:absence_create_pour', args=[ecole['etranger'].pk])).status_code == 404


def test_liste_et_bilan_mensuel_par_agent(ecole):
    agent = ecole['agent']
    _absence(agent, date(2026, 10, 5), date(2026, 10, 7))
    _absence(agent, date(2026, 10, 12), date(2026, 10, 12), motif='MALADIE', justifiee=True)
    _absence(agent, date(2026, 11, 2), date(2026, 11, 2))
    _absence(ecole['etranger'], date(2026, 10, 5), date(2026, 10, 5))
    reponse = ecole['client'].get(reverse('personnel:absence_list'), {'mois': '2026-10'})
    assert reponse.status_code == 200
    assert len(reponse.context['absences']) == 2, 'octobre seulement, établissement seulement'
    bilan = reponse.context['bilan']
    assert len(bilan) == 1 and bilan[0]['membre'] == agent
    assert (bilan[0]['absences'], bilan[0]['jours'], bilan[0]['non_justifies'], bilan[0]['retenus']) == (2, 4, 3, 3)
    html = reponse.content.decode()
    assert 'KABORE' in html and 'AILLEURS' not in html
    # Filtre par agent : toutes ses absences, tous mois confondus
    reponse = ecole['client'].get(reverse('personnel:absence_list'), {'personnel': str(agent.pk)})
    assert len(reponse.context['absences']) == 3 and reponse.context['membre'] == agent
    # Mois invalide → mois courant, sans erreur
    assert ecole['client'].get(reverse('personnel:absence_list'), {'mois': 'n-importe'}).status_code == 200


def test_suppression_d_une_absence(ecole):
    c = ecole['client']
    absence = _absence(ecole['agent'], date(2026, 10, 5), date(2026, 10, 5))
    etrangere = _absence(ecole['etranger'], date(2026, 10, 5), date(2026, 10, 5))
    assert c.get(reverse('personnel:absence_delete', args=[absence.pk])).status_code == 405
    assert c.post(reverse('personnel:absence_delete', args=[etrangere.pk])).status_code == 404
    reponse = c.post(reverse('personnel:absence_delete', args=[absence.pk]), {'suivant': 'fiche'})
    assert reponse.status_code == 302 and reponse.url == reverse('personnel:detail', args=[ecole['agent'].pk])
    assert not AbsencePersonnel.objects.filter(pk=absence.pk).exists() and AbsencePersonnel.objects.filter(pk=etrangere.pk).exists()


def test_la_fiche_de_l_agent_affiche_ses_absences_recentes(ecole):
    _absence(ecole['agent'], date(2026, 10, 5), date(2026, 10, 7))
    html = ecole['client'].get(reverse('personnel:detail', args=[ecole['agent'].pk])).content.decode()
    assert 'Absences récentes' in html and '05/10/2026' in html
    assert reverse('personnel:absence_create_pour', args=[ecole['agent'].pk]) in html
    assert reverse('personnel:attestation_travail', args=[ecole['agent'].pk]) in html


def test_le_menu_et_les_droits_connaissent_les_absences(ecole):
    from parametres.droits import PREFIXES_FONCTIONNALITES
    assert '/personnel/absences/' in PREFIXES_FONCTIONNALITES
    html = ecole['client'].get(reverse('personnel:personnel_list')).content.decode()
    assert reverse('personnel:absence_list') in html


# ── Attestation de travail ───────────────────────────────────────────────────

def test_attestation_de_travail_apercu_et_pdf(ecole, mocker):
    c, agent = ecole['client'], ecole['agent']
    poste = baker.make('parametres.Poste', etablissement=ecole['etab'], titre='Professeur de mathématiques')
    baker.make('personnel.InscriptionPersonnel', personnel=agent, annee_scolaire=ecole['annee'], poste=poste)
    reponse = c.get(reverse('personnel:attestation_travail', args=[agent.pk]))
    assert reponse.status_code == 200
    html = reponse.content.decode()
    assert 'Attestation de travail' in html and 'KABORE' in html and 'Professeur de mathématiques' in html
    assert 'CAP-CEG' in html and 'Contrat à durée déterminée' in html
    weasy = mocker.patch('core.pdf.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    reponse = c.get(reverse('personnel:attestation_travail', args=[agent.pk]), {'format': 'pdf'})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert 'attestation_travail_KABORE_Salif.pdf' in reponse['Content-Disposition']
    source = weasy.call_args.kwargs['string']
    assert '@page { size: A4 portrait' in source and '<h1>Attestation de travail</h1>' in source and 'KABORE' in source


def test_attestation_d_un_agent_d_un_autre_etablissement_introuvable(ecole):
    assert ecole['client'].get(reverse('personnel:attestation_travail', args=[ecole['etranger'].pk])).status_code == 404
