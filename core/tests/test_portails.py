"""Lot G — portails : vie scolaire du portail parent (emploi du temps, absences, dépôt de justificatif) et portail
élève enrichi (travail à faire, notes, moyennes, emploi du temps, absences)."""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.validators import validate_piece_jointe
from presences.models import Justification, Presence

pytestmark = pytest.mark.django_db


@pytest.fixture
def famille():
    etab = baker.make('etablissements.Etablissement')
    aujourdhui = timezone.localdate()
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=aujourdhui - timedelta(days=30), date_fin=aujourdhui + timedelta(days=240))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='5e B', actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Awa', date_naissance=date(2013, 4, 2), photo='')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut='AFFECTE')
    maths = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, est_actif=True,
                       coefficient=Decimal('4'), matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'))
    baker.make('viescolaire.SeanceCours', enseignement=maths, jour=1, heure_debut=time(7, 30), heure_fin=time(9, 30),
               salle='S12')
    appel = baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=aujourdhui - timedelta(days=2))
    baker.make('presences.Presence', appel=appel, inscription=inscription, statut=Presence.StatutChoices.ABSENT)
    appel2 = baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=aujourdhui - timedelta(days=1))
    baker.make('presences.Presence', appel=appel2, inscription=inscription, statut=Presence.StatutChoices.RETARD,
               minutes_retard=10)
    parent = baker.make('accounts.User', etablissement=etab, role='PARENT', must_change_password=False)
    parent.eleves_lies.add(eleve)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'eleve': eleve, 'inscription': inscription,
            'maths': maths, 'parent': parent, 'aujourdhui': aujourdhui}


# ── G2 : portail parent, vie scolaire ─────────────────────────────────────────

def test_vie_scolaire_edt_absences_et_navigation(client, famille):
    client.force_login(famille['parent'])
    reponse = client.get(reverse('core:portail_parent_vie_scolaire'))
    assert reponse.status_code == 200
    enfant = reponse.context['enfants'][0]
    assert enfant['inscription'] == famille['inscription']
    assert enfant['compteurs'] == {'absences': 1, 'retards': 1, 'excusees': 0}
    assert [s.salle for j in enfant['edt'] for s in j['seances']] == ['S12']
    html = reponse.content.decode()
    assert 'Mathématiques' in html and 'S12' in html and 'Vie scolaire' in html
    assert reverse('core:portail_parent_bulletins') in html, 'barre de navigation commune'


def test_depot_de_justificatif_par_le_parent(client, famille):
    client.force_login(famille['parent'])
    hier = famille['aujourdhui'] - timedelta(days=1)
    pdf = SimpleUploadedFile('certificat.pdf', b'%PDF-1.4\n%fake\n', content_type='application/pdf')
    reponse = client.post(reverse('core:portail_parent_justifier'), {
        'inscription': famille['inscription'].pk, 'date_debut': (hier - timedelta(days=1)).isoformat(),
        'date_fin': hier.isoformat(), 'motif': '  Paludisme,   certificat joint  ', 'document': pdf,
    })
    assert reponse.status_code == 302 and reponse.url == reverse('core:portail_parent_vie_scolaire')
    j = Justification.objects.get()
    assert (j.inscription, j.deposee_par, j.statut) == (famille['inscription'], famille['parent'], 'EN_ATTENTE')
    assert j.motif == 'Paludisme, certificat joint' and j.nb_jours == 2 and j.via_portail
    assert j.document.name.endswith('.pdf')
    j.document.delete(save=False)


@pytest.mark.parametrize('champs, attendu', [
    ({'date_debut': '', 'date_fin': ''}, 'Indiquez les dates'),
    ({'date_fin': 'avant'}, 'antérieure à la date de début'),
    ({'date_debut': 'demain', 'date_fin': 'demain'}, 'se dépose après'),
    ({'motif': '   '}, 'Indiquez le motif'),
])
def test_justificatif_incomplet_refuse(client, famille, champs, attendu):
    client.force_login(famille['parent'])
    hier, demain = famille['aujourdhui'] - timedelta(days=1), famille['aujourdhui'] + timedelta(days=1)
    valeurs = {'demain': demain.isoformat(), 'avant': (hier - timedelta(days=3)).isoformat()}
    donnees = {'inscription': famille['inscription'].pk, 'date_debut': hier.isoformat(), 'date_fin': hier.isoformat(),
               'motif': 'Maladie'}
    donnees.update({k: valeurs.get(v, v) for k, v in champs.items()})
    reponse = client.post(reverse('core:portail_parent_justifier'), donnees, follow=True)
    assert attendu in reponse.content.decode()
    assert not Justification.objects.exists()


def test_parent_ne_justifie_que_pour_ses_enfants(client, famille):
    autre = baker.make('accounts.User', etablissement=famille['etab'], role='PARENT', must_change_password=False)
    client.force_login(autre)
    hier = famille['aujourdhui'] - timedelta(days=1)
    reponse = client.post(reverse('core:portail_parent_justifier'), {
        'inscription': famille['inscription'].pk, 'date_debut': hier.isoformat(), 'date_fin': hier.isoformat(),
        'motif': 'Maladie'}, follow=True)
    assert 'Enfant introuvable' in reponse.content.decode() and not Justification.objects.exists()


def test_piece_jointe_controlee():
    validate_piece_jointe(SimpleUploadedFile('ok.pdf', b'%PDF-1.7 ...'))
    with pytest.raises(ValidationError, match='PDF valide'):
        validate_piece_jointe(SimpleUploadedFile('faux.pdf', b'MZ\x90\x00 executable'))
    with pytest.raises(ValidationError, match='Format non autorisé'):
        validate_piece_jointe(SimpleUploadedFile('script.exe', b'%PDF-'))
    with pytest.raises(ValidationError, match='trop volumineux'):
        validate_piece_jointe(SimpleUploadedFile('gros.pdf', b'%PDF-' + b'0' * 20, content_type='application/pdf'),
                              max_size_bytes=10)


def test_justificatif_du_portail_signale_au_secretariat(client, famille):
    j = Justification.objects.create(inscription=famille['inscription'], date_debut=famille['aujourdhui'],
                                     date_fin=famille['aujourdhui'], motif='Maladie', deposee_par=famille['parent'])
    assert j.via_portail
    secretaire = baker.make('accounts.User', etablissement=famille['etab'], role='SECRETAIRE', is_superuser=True,
                            must_change_password=False)
    client.force_login(secretaire)
    assert 'Portail parent' in client.get(reverse('presences:justification_list')).content.decode()


def test_parent_accede_a_la_signature_du_bulletin(client, famille):
    """Le préfixe /bulletins/parent/ (consultation et signature) fait partie du périmètre du rôle PARENT."""
    client.force_login(famille['parent'])
    reponse = client.get(reverse('bulletins:bulletin_parent_consulter', kwargs={'token': 'inexistant'}))
    assert reponse.status_code != 302 or '/portail/parent/' not in reponse.get('Location', '')


# ── G1 : portail élève ────────────────────────────────────────────────────────

def test_portail_eleve_enrichi(client, famille):
    eleve_user = baker.make('accounts.User', etablissement=famille['etab'], role='ELEVE', must_change_password=False)
    eleve_user.eleves_lies.add(famille['eleve'])
    t1 = baker.make('pedagogie.Trimestre', annee_scolaire=famille['annee'], numero=1, nom='Trimestre 1',
                    date_debut=famille['aujourdhui'] - timedelta(days=30), date_fin=famille['aujourdhui'] + timedelta(days=60))
    ev = baker.make('pedagogie.Evaluation', enseignement=famille['maths'], trimestre=t1, titre='Devoir 1',
                    bareme=Decimal('20'), statut='TERMINEE', date_planifiee=famille['aujourdhui'] - timedelta(days=3),
                    type_evaluation=baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1'), nb_meilleures_notes=0))
    baker.make('pedagogie.Note', inscription=famille['inscription'], evaluation=ev, valeur=Decimal('15.5'))
    baker.make('pedagogie.Resultat', inscription=famille['inscription'], enseignement=famille['maths'], trimestre=t1,
               moyenne=Decimal('15.50'), moyenne_sur_20=Decimal('15.50'), nb_notes=1)
    baker.make('pedagogie.CahierTextes', enseignement=famille['maths'], date=famille['aujourdhui'],
               contenu='Fractions', devoirs='Exercices 4 et 5 p. 32',
               date_remise_devoirs=famille['aujourdhui'] + timedelta(days=2))
    client.force_login(eleve_user)
    reponse = client.get(reverse('core:portail_eleve'))
    assert reponse.status_code == 200
    ctx = reponse.context
    assert ctx['compteurs'] == {'absences': 1, 'retards': 1, 'excusees': 0}
    assert [n.valeur for n in ctx['notes_recentes']] == [Decimal('15.5')]
    assert [d.devoirs for d in ctx['devoirs_a_venir']] == ['Exercices 4 et 5 p. 32']
    assert [(t.nom, [r.moyenne for r in rs]) for t, rs in ctx['moyennes_periodes']] == [('Trimestre 1', [Decimal('15.50')])]
    html = reponse.content.decode()
    for attendu in ('Travail à faire', 'Exercices 4 et 5 p. 32', '15,50', 'S12', 'Mes absences et retards'):
        assert attendu in html, attendu
