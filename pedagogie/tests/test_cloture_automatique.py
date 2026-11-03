"""Clôture automatique en fin de trimestre et dérogation motivée de la direction (5.47.4)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from parametres import droits
from parametres.models import DroitAcces
from pedagogie.models import MoyenneGenerale, Note, Trimestre
from pedagogie.utils import CalculateurMoyenne

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexte(client):
    auj = date.today()
    etab = baker.make('etablissements.Etablissement', nom='Lycée Wend-Kuuni', ville='Ouagadougou')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='Lycée Wend-Kuuni')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=auj - timedelta(days=90), date_fin=auj + timedelta(days=180))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='TRAORE', prenom='Moussa',
                      email='moussa@ecole.bf')
    enseignement = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, personnel=prof,
                              est_actif=True, coefficient=Decimal('4'),
                              matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'))
    devoir = baker.make('pedagogie.TypeEvaluation', nom='Devoir', coefficient=Decimal('1'), nb_meilleures_notes=0)
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', first_name='Issa',
                           last_name='OUEDRAOGO', username='dir.issa', must_change_password=False)
    enseignant = baker.make('accounts.User', etablissement=etab, role='ENSEIGNANT', email='moussa@ecole.bf',
                            username='ens.moussa', must_change_password=False)
    eleve = baker.make('inscriptions.Eleve', nom='SAWADOGO', prenom='Awa', photo='')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee,
                             statut='ACTIF')

    def creer_periode(numero, fin, nom=None):
        lib = nom or f'Trimestre {numero}'
        debut = fin - timedelta(days=60)
        periode = baker.make('parametres.PeriodeEvaluation', etablissement=etab, annee_scolaire=annee,
                             type_periode='TRIMESTRE', nom=lib, numero=numero, date_debut=debut, date_fin=fin)
        trimestre = Trimestre.objects.pour_periode(periode)
        evaluation = baker.make('pedagogie.Evaluation', enseignement=enseignement, trimestre=trimestre,
                                type_evaluation=devoir, titre=f'Devoir T{numero}', bareme=Decimal('20'),
                                statut='TERMINEE', date_planifiee=fin - timedelta(days=5))
        baker.make('pedagogie.Note', inscription=inscription, evaluation=evaluation, valeur=Decimal('14'))
        trimestre.derogation_ouverte = True
        CalculateurMoyenne.recalculer_classe(classe, trimestre)
        trimestre.derogation_ouverte = False
        return periode, trimestre, evaluation

    return {
        'auj': auj, 'etab': etab, 'annee': annee, 'classe': classe, 'enseignement': enseignement,
        'devoir': devoir, 'directeur': directeur, 'enseignant': enseignant, 'inscription': inscription,
        'creer_periode': creer_periode,
    }


def test_cloture_automatique_au_lendemain_de_la_date_de_fin(client, contexte):
    auj = contexte['auj']
    # Dernier jour du trimestre : encore ouverte jusqu'à 23 h 59.
    _, trim_jour_j, ev_jour_j = contexte['creer_periode'](1, fin=auj)
    assert not trim_jour_j.echue and not trim_jour_j.verrouille
    client.force_login(contexte['enseignant'])
    saisie_j = reverse('pedagogie:evaluation_saisie', kwargs={'pk': ev_jour_j.pk})
    assert client.post(saisie_j, {f"note_{contexte['inscription'].pk}": '16'}).status_code == 302
    assert Note.objects.get(inscription=contexte['inscription'], evaluation=ev_jour_j).valeur == Decimal('16')

    # Lendemain de la date de fin : verrouillée automatiquement sans action de la direction.
    periode_echue, trim_echu, ev_echu = contexte['creer_periode'](2, fin=auj - timedelta(days=1))
    assert trim_echu.echue and trim_echu.verrouille and periode_echue.verrouillee
    assert not trim_echu.notes_saisies and not periode_echue.cloturee

    # Écriture refusée partout (notes, évaluations, appréciations, compétences, recalcul).
    saisie = reverse('pedagogie:evaluation_saisie', kwargs={'pk': ev_echu.pk})
    html_saisie = client.get(saisie).content.decode()
    assert '<fieldset disabled' in html_saisie
    assert f"est clôturé depuis le {trim_echu.date_fin:%d/%m/%Y}" in html_saisie
    client.post(saisie, {f"note_{contexte['inscription'].pk}": '3'})
    assert Note.objects.get(inscription=contexte['inscription'], evaluation=ev_echu).valeur == Decimal('14')

    resp_eval = client.post(reverse('pedagogie:evaluation_create'), {
        'enseignement': contexte['enseignement'].pk, 'type_evaluation': contexte['devoir'].pk,
        'periode': periode_echue.pk, 'titre': 'Tardif', 'date_planifiee': str(auj),
        'bareme': '20', 'duree_minutes': '60', 'statut': 'PLANIFIEE',
    })
    assert resp_eval.status_code == 200 and 'est clôturé' in str(resp_eval.context['form'].errors['periode'])

    client.post(reverse('pedagogie:appreciations_saisir', args=[contexte['enseignement'].pk, trim_echu.pk]),
                {f"appr_{contexte['inscription'].pk}": 'Hors délai'})
    assert contexte['enseignement'].resultats.get(inscription=contexte['inscription'], trimestre=trim_echu).appreciation == ''

    comp = baker.make('pedagogie.Competence', cycle=contexte['classe'].cycle, actif=True)
    assert client.post(reverse('pedagogie:competence_sauvegarder'), {
        'inscription': contexte['inscription'].pk, 'competence': comp.pk, 'trimestre': trim_echu.pk, 'niveau': 'ACQUIS',
    }).status_code == 403

    Note.objects.filter(inscription=contexte['inscription'], evaluation=ev_echu).update(valeur=Decimal('2'))
    assert CalculateurMoyenne.recalculer_classe(contexte['classe'], trim_echu) == 0
    assert MoyenneGenerale.objects.get(inscription=contexte['inscription'], trimestre=trim_echu).moyenne == Decimal('14.00')

    # Consultation et bulletins restent accessibles.
    client.force_login(contexte['directeur'])
    assert client.get(reverse('pedagogie:resultat_classe', args=[contexte['classe'].pk]),
                      {'trimestre': trim_echu.pk}).status_code == 200
    assert client.get(reverse('pedagogie:bulletin_apercu',
                              args=[contexte['inscription'].pk, trim_echu.pk])).status_code == 200


def test_derogation_motivee_direction_et_refermeture_journalisees(client, contexte):
    periode, trimestre, evaluation = contexte['creer_periode'](1, fin=contexte['auj'] - timedelta(days=5))
    url_cloture = reverse('parametres:periode_cloture', kwargs={'pk': periode.pk})
    url_liste = reverse('parametres:periode_list')
    saisie = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    client.force_login(contexte['directeur'])
    html_liste = client.get(url_liste, HTTP_HX_REQUEST='true').content.decode()
    assert f"Clôturée (fin {periode.date_fin:%d/%m/%Y})" in html_liste
    assert 'Rouvrir la période (dérogation motivée)' in html_liste

    # Modale de dérogation servie en GET ; motif vide refusé (modale et appel direct).
    modale = client.get(url_cloture, HTTP_HX_REQUEST='true')
    assert modale.status_code == 200 and 'Motif de la dérogation' in modale.content.decode()
    erreur_modale = client.post(url_cloture, {'motif': '   '}, HTTP_HX_REQUEST='true', HTTP_HX_TARGET='modal-container')
    trimestre.refresh_from_db()
    assert erreur_modale.status_code == 200 and 'Le motif de réouverture est obligatoire.' in erreur_modale.content.decode()
    assert trimestre.verrouille
    assert client.post(url_cloture, {'motif': ''}).status_code == 400
    with pytest.raises(ValueError, match='obligatoire'):
        trimestre.cloturer(ouvert=True, utilisateur=contexte['directeur'], motif='  ')

    # Réouverture motivée par la direction.
    motif = 'Erreur matérielle sur la copie de SAWADOGO Awa'
    ouverture = client.post(url_cloture, {'motif': motif}, HTTP_HX_REQUEST='true', HTTP_HX_TARGET='modal-container')
    trimestre.refresh_from_db()
    periode.refresh_from_db()
    assert ouverture.status_code == 204 and ouverture['HX-Trigger'] == 'parametreUpdated'
    assert not trimestre.verrouille and trimestre.derogation_ouverte and periode.derogation_ouverte
    assert f'Réouverture par Issa OUEDRAOGO : {motif}' in trimestre.journal_cloture

    html_liste = client.get(url_liste, HTTP_HX_REQUEST='true').content.decode()
    assert 'Dérogation ouverte' in html_liste and motif in html_liste

    # L'enseignant corrige la note pendant la dérogation.
    client.force_login(contexte['enseignant'])
    client.post(saisie, {f"note_{contexte['inscription'].pk}": '17'})
    assert Note.objects.get(inscription=contexte['inscription'], evaluation=evaluation).valeur == Decimal('17')
    assert MoyenneGenerale.objects.get(inscription=contexte['inscription'], trimestre=trimestre).moyenne == Decimal('17.00')

    # La direction referme la dérogation : verrou rétabli et trace complète conservée.
    client.force_login(contexte['directeur'])
    fermeture = client.post(url_cloture, HTTP_HX_REQUEST='true')
    trimestre.refresh_from_db()
    periode.refresh_from_db()
    assert fermeture.status_code == 204
    assert trimestre.verrouille and not trimestre.derogation_ouverte and not periode.derogation_ouverte
    lignes = trimestre.journal_cloture.splitlines()
    assert len(lignes) == 2
    assert 'Réouverture par Issa OUEDRAOGO' in lignes[0] and 'Clôture par Issa OUEDRAOGO' in lignes[1]

    modale_apres = client.get(url_cloture, HTTP_HX_REQUEST='true').content.decode()
    assert motif in modale_apres and 'Clôture par Issa OUEDRAOGO' in modale_apres

    client.force_login(contexte['enseignant'])
    client.post(saisie, {f"note_{contexte['inscription'].pk}": '8'})
    assert Note.objects.get(inscription=contexte['inscription'], evaluation=evaluation).valeur == Decimal('17')


def test_derogation_interdite_hors_direction_et_contournement_date_fin_bloque(client, contexte):
    periode, trimestre, _ = contexte['creer_periode'](1, fin=contexte['auj'] - timedelta(days=3))
    url_cloture = reverse('parametres:periode_cloture', kwargs={'pk': periode.pk})

    for role in ('ENSEIGNANT', 'SECRETAIRE', 'COMPTABLE'):
        utilisateur = baker.make('accounts.User', etablissement=contexte['etab'], role=role, must_change_password=False)
        client.force_login(utilisateur)
        assert client.get(url_cloture, HTTP_HX_REQUEST='true').status_code == 403
        assert client.post(url_cloture, {'motif': 'Tentative'}, HTTP_HX_REQUEST='true').status_code == 403
        assert client.post(url_cloture, {'motif': 'Tentative'}).status_code == 302
        trimestre.refresh_from_db()
        assert trimestre.verrouille

    # Même si le secrétariat reçoit l'accès à l'écran Périodes sans l'action « cloturer », il ne peut pas
    # repousser la date de fin d'une période échue pour contourner le verrou.
    secretaire = baker.make('accounts.User', etablissement=contexte['etab'], role='SECRETAIRE', must_change_password=False)
    acces = DroitAcces.objects.create(role='SECRETAIRE', module='parametres', fonctionnalite='/parametres/periodes/',
                                      action='', autorise=True)
    droits.invalider_cache()
    try:
        client.force_login(secretaire)
        nouvelle_fin = contexte['auj'] + timedelta(days=15)
        refus = client.post(reverse('parametres:periode_edit', kwargs={'pk': periode.pk}), {
            'nom': periode.nom, 'type_periode': 'TRIMESTRE', 'numero': 1,
            'annee_scolaire': contexte['annee'].pk, 'date_debut': str(periode.date_debut),
            'date_fin': str(nouvelle_fin),
        })
        periode.refresh_from_db()
        trimestre.refresh_from_db()
        assert refus.status_code == 200 and 'Seule la direction' in refus.content.decode()
        assert trimestre.verrouille and periode.date_fin < contexte['auj']
    finally:
        acces.delete()
        droits.invalider_cache()

    # La direction, elle, peut reporter l'échéance officielle et le trimestre suit la nouvelle date.
    client.force_login(contexte['directeur'])
    nouvelle_fin = contexte['auj'] + timedelta(days=15)
    ok = client.post(reverse('parametres:periode_edit', kwargs={'pk': periode.pk}), {
        'nom': periode.nom, 'type_periode': 'TRIMESTRE', 'numero': 1,
        'annee_scolaire': contexte['annee'].pk, 'date_debut': str(periode.date_debut),
        'date_fin': str(nouvelle_fin),
    })
    trimestre.refresh_from_db()
    assert ok.status_code == 204 and trimestre.date_fin == nouvelle_fin and not trimestre.verrouille


def test_reouverture_avant_echeance_laisse_la_cloture_automatique_agir_en_fin_de_trimestre(client, contexte):
    periode, trimestre, _ = contexte['creer_periode'](1, fin=contexte['auj'] + timedelta(days=10))
    url_cloture = reverse('parametres:periode_cloture', kwargs={'pk': periode.pk})
    client.force_login(contexte['directeur'])

    assert client.post(url_cloture).status_code == 204
    trimestre.refresh_from_db()
    assert trimestre.verrouille

    assert client.post(url_cloture, {'motif': 'Devoir de rattrapage avant la fin du trimestre'}).status_code == 204
    trimestre.refresh_from_db()
    assert not trimestre.verrouille and not trimestre.derogation_ouverte

    # L'échéance passe : le verrou automatique s'applique sans intervention.
    Trimestre.objects.filter(pk=trimestre.pk).update(date_fin=contexte['auj'] - timedelta(days=1))
    trimestre.refresh_from_db()
    assert trimestre.verrouille


def test_cloture_annee_referme_toute_derogation_ouverte(client, contexte):
    auj = contexte['auj']
    passee = baker.make('parametres.AnneeScolaire', etablissement=contexte['etab'], libelle='2025-2026',
                        date_debut=auj - timedelta(days=400), date_fin=auj - timedelta(days=120), est_courante=False)
    periode = baker.make('parametres.PeriodeEvaluation', etablissement=contexte['etab'], annee_scolaire=passee,
                         nom='Trimestre 3', numero=3, date_debut=auj - timedelta(days=200),
                         date_fin=auj - timedelta(days=120), cloturee=False, derogation_ouverte=True)
    trimestre = Trimestre.objects.pour_periode(periode)
    assert not trimestre.verrouille and trimestre.derogation_ouverte

    client.force_login(contexte['directeur'])
    reponse = client.post(reverse('parametres:annee_cloture', kwargs={'pk': passee.pk}))
    periode.refresh_from_db()
    trimestre.refresh_from_db()
    assert reponse.status_code == 204
    assert trimestre.verrouille and not trimestre.derogation_ouverte and not periode.derogation_ouverte
    assert "Clôture de l'année 2025-2026" in trimestre.journal_cloture
