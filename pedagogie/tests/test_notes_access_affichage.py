"""Masquage des notes enregistrées et des bulletins sans paiement net admissible."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from pedagogie.models import MoyenneGenerale, Resultat

pytestmark = pytest.mark.django_db


@pytest.fixture
def resultats_prives(client):
    """Deux élèves avec des notes anciennes : un paiement partiel, aucun paiement pour l'autre."""
    etab = baker.make('etablissements.Etablissement', nom='ÉCOLE PRIVÉE', ville='Sabou')
    identite = baker.make(
        'parametres.IdentiteEtablissement',
        etablissement=etab,
        nom_etablissement='ÉCOLE PRIVÉE',
        type_etablissement='PUBLIC',
    )
    annee = baker.make(
        'parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
        date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30),
    )
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    fin_t1 = max(date(2026, 12, 20), date.today() + timedelta(days=30))
    trimestre = baker.make(
        'pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
        date_debut=date(2026, 10, 1), date_fin=fin_t1,
    )
    periode = baker.make(
        'parametres.PeriodeEvaluation', etablissement=etab, annee_scolaire=annee,
        type_periode='TRIMESTRE', nom='Trimestre 1', numero=1,
        date_debut=date(2026, 10, 1), date_fin=fin_t1,
    )
    matiere = baker.make('pedagogie.Matiere', nom='Mathématiques', code='MATH')
    enseignement = baker.make(
        'pedagogie.Enseignement', classe=classe, annee_scolaire=annee,
        matiere=matiere, est_actif=True, coefficient=Decimal('1'),
    )
    type_evaluation = baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1'), nb_meilleures_notes=0)
    evaluation = baker.make(
        'pedagogie.Evaluation', enseignement=enseignement, trimestre=trimestre,
        type_evaluation=type_evaluation, titre='Devoir ancien', bareme=Decimal('20'),
        statut='TERMINEE', date_planifiee=date(2026, 11, 5),
    )

    payant = baker.make(
        'inscriptions.Inscription',
        eleve=baker.make('inscriptions.Eleve', nom='PAYANT', prenom='Awa'),
        classe=classe, annee_scolaire=annee, statut='ACTIF',
    )
    impaye = baker.make(
        'inscriptions.Inscription',
        eleve=baker.make('inscriptions.Eleve', nom='IMPAYE', prenom='Boubacar'),
        classe=classe, annee_scolaire=annee, statut='ACTIF',
    )
    rubrique = baker.make(
        'parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCO',
        actif=True, soumise_plafond=True,
    )
    # Un montant volontairement faible vérifie qu'un paiement partiel positif reste autorisé.
    baker.make(
        'finances.Paiement', inscription=payant, rubrique=rubrique,
        montant=Decimal('1'), date_paiement=date(2026, 10, 2),
    )

    # Ces notes ont été enregistrées avant le passage de l'établissement en mode privé.
    baker.make('pedagogie.Note', inscription=payant, evaluation=evaluation, valeur=Decimal('12'))
    baker.make('pedagogie.Note', inscription=impaye, evaluation=evaluation, valeur=Decimal('19'))
    for inscription, moyenne, note in (
        (payant, Decimal('12.00'), Decimal('12.00')),
        (impaye, Decimal('19.00'), Decimal('19.00')),
    ):
        baker.make(
            'pedagogie.Resultat', inscription=inscription, enseignement=enseignement,
            trimestre=trimestre, moyenne=moyenne, moyenne_sur_20=moyenne,
            nb_notes=1, coefficient_utilise=Decimal('1.00'),
        )
        baker.make(
            'pedagogie.MoyenneGenerale', inscription=inscription, trimestre=trimestre,
            moyenne=moyenne, moyenne_sur_20=moyenne, rang=1 if moyenne == 19 else 2,
            total_points=note, total_coefficients=Decimal('1.00'), nb_matieres_total=1,
        )

    identite.type_etablissement = 'PRIVE'
    identite.save(update_fields=['type_etablissement', 'updated_at'])
    utilisateur = baker.make(
        'accounts.User', etablissement=etab, is_superuser=True, role='SUPER_ADMIN',
        must_change_password=False,
    )
    client.force_login(utilisateur)
    return SimpleNamespace(
        client=client, etab=etab, annee=annee, classe=classe, cycle=cycle,
        trimestre=trimestre, periode=periode, enseignement=enseignement,
        payant=payant, impaye=impaye,
    )


def _ids(lignes, cle='inscription'):
    return {ligne[cle].pk for ligne in lignes}


def test_releves_et_tableaux_excluent_les_notes_de_l_inscription_bloquee(resultats_prives, mocker):
    c = resultats_prives
    filtres = {
        'annee': c.annee.pk,
        'classe': c.classe.pk,
        'enseignement': c.enseignement.pk,
        'periode': c.periode.pk,
    }

    releve = c.client.get(reverse('pedagogie:releve_notes'), filtres)
    assert releve.status_code == 200
    assert _ids(releve.context['table']) == {c.payant.pk}
    assert 'IMPAYE' not in releve.content.decode()

    resultats = c.client.get(
        reverse('pedagogie:resultat_classe', kwargs={'class_id': c.classe.pk}),
        {'annee': c.annee.pk, 'trimestre': c.trimestre.pk},
    )
    assert resultats.status_code == 200
    assert {ins.pk for ins in resultats.context['inscriptions']} == {c.payant.pk}
    assert set(resultats.context['moyennes_gen']) == {c.payant.pk}

    bilan = c.client.get(reverse('pedagogie:bilan_periodes'), {'annee': c.annee.pk})
    assert bilan.status_code == 200
    stats_bilan = next(
        ligne['stats'] for periode in bilan.context['periodes_data']
        for ligne in periode['lignes'] if ligne['classe'].pk == c.classe.pk
    )
    assert stats_bilan['nb_eleves'] == 1 and stats_bilan['moy_max'] == 12.0

    filtres_moyennes = {
        'annee': c.annee.pk, 'classe': c.classe.pk, 'trimestre': c.trimestre.pk,
    }
    moyennes = c.client.get(reverse('pedagogie:moyennes_disciplines'), filtres_moyennes)
    assert moyennes.status_code == 200
    assert _ids(moyennes.context['lignes']) == {c.payant.pk}

    render = mocker.patch('pedagogie.views.resultats.render_to_string', return_value='<html>relevé</html>')
    html = mocker.patch('pedagogie.views.resultats.HTML')
    html.return_value.write_pdf.return_value = b'%PDF-test'
    for nom_url in ('pedagogie:releve_notes_pdf', 'pedagogie:fiche_discipline_pdf'):
        pdf = c.client.get(reverse(nom_url), filtres)
        assert pdf.status_code == 200 and pdf['Content-Type'] == 'application/pdf'
        assert _ids(render.call_args.args[1]['table']) == {c.payant.pk}

    render.reset_mock()
    pdf = c.client.get(reverse('pedagogie:moyennes_disciplines_pdf'), filtres_moyennes)
    assert pdf.status_code == 200 and pdf['Content-Type'] == 'application/pdf'
    assert _ids(render.call_args.args[1]['lignes']) == {c.payant.pk}

    render.reset_mock()
    bilan_pdf = c.client.get(reverse('pedagogie:bilan_pdf'), {
        'annee': c.annee.pk, 'classe': c.classe.pk, 'trimestre': c.trimestre.pk,
    })
    assert bilan_pdf.status_code == 200 and bilan_pdf['Content-Type'] == 'application/pdf'
    context_bilan_pdf = render.call_args.args[1]
    stats_pdf = context_bilan_pdf['periodes_data'][0]['lignes'][0]['stats']
    assert stats_pdf['nb_eleves'] == 1 and stats_pdf['moy_max'] == 12.0

    # Les données historiques restent intactes : la règle masque, elle n'efface pas.
    from pedagogie.models import Note
    assert Note.objects.filter(inscription=c.impaye).exists()
    assert Resultat.objects.filter(inscription=c.impaye).exists()
    assert MoyenneGenerale.objects.filter(inscription=c.impaye).exists()


def test_acces_individuels_aux_bulletins_et_saisies_refuse_pour_inscription_bloquee(resultats_prives, mocker):
    c = resultats_prives
    routes_trimestrielles = (
        'pedagogie:bulletin_apercu', 'pedagogie:bulletin_pdf', 'pedagogie:bulletin_duplicata_pdf',
    )
    mocker.patch('pedagogie.views.bulletins.HTML')
    for nom_url in routes_trimestrielles:
        url = reverse(nom_url, kwargs={'inscription_id': c.impaye.pk, 'trimestre_id': c.trimestre.pk})
        assert c.client.get(url).status_code == 404

    for nom_url in ('pedagogie:bulletin_annuel_apercu', 'pedagogie:bulletin_annuel_pdf'):
        url = reverse(nom_url, kwargs={'inscription_id': c.impaye.pk})
        assert c.client.get(url, {'annee': c.annee.pk}).status_code == 404

    mocker.patch('pedagogie.views.competences.HTML')
    competence_pdf = reverse(
        'pedagogie:competences_bulletin_pdf',
        kwargs={'inscription_id': c.impaye.pk, 'trimestre_id': c.trimestre.pk},
    )
    assert c.client.get(competence_pdf).status_code == 404

    saisir = reverse(
        'bulletins:bulletin_saisir',
        kwargs={'inscription_id': c.impaye.pk, 'trimestre_id': c.trimestre.pk},
    )
    publier = reverse(
        'bulletins:bulletin_publier',
        kwargs={'inscription_id': c.impaye.pk, 'trimestre_id': c.trimestre.pk},
    )
    assert c.client.get(saisir).status_code == 404
    assert c.client.post(publier).status_code == 403

    annuel = reverse(
        'bulletins:bulletin_annuel', kwargs={'inscription_id': c.impaye.pk, 'annee_pk': c.annee.pk},
    )
    assert c.client.get(annuel).status_code == 404
    mocker.patch('bulletins.views.HTML')
    annuel_pdf = reverse(
        'bulletins:bulletin_annuel_pdf', kwargs={'inscription_id': c.impaye.pk, 'annee_pk': c.annee.pk},
    )
    assert c.client.get(annuel_pdf).status_code == 404


def test_listes_et_exports_en_lot_ne_contiennent_que_les_inscriptions_autorisees(resultats_prives, mocker):
    c = resultats_prives
    url_liste = reverse(
        'bulletins:bulletins_classe', kwargs={'class_id': c.classe.pk, 'trimestre_id': c.trimestre.pk},
    )
    liste = c.client.get(url_liste)
    assert liste.status_code == 200
    assert {ligne['inscription'].pk for ligne in liste.context['lignes']} == {c.payant.pk}

    annuel_index = c.client.get(
        reverse('bulletins:bulletin_annuel_index'),
        {'classe': c.classe.pk, 'annee': c.annee.pk},
    )
    assert annuel_index.status_code == 200
    assert {ins.pk for ins in annuel_index.context['inscriptions']} == {c.payant.pk}

    rendu = mocker.patch(
        'pedagogie.views.bulletins.render_to_string',
        side_effect=lambda _tpl, ctx: str(ctx.get('inscription', ctx['students_data'][0]['inscription']).pk)
        if 'students_data' in ctx else str(ctx['inscription'].pk),
    )
    pdf = mocker.patch('pedagogie.views.bulletins.HTML')
    pdf.lot.return_value = b'%PDF-test'
    trimestriel_batch = c.client.get(reverse(
        'pedagogie:bulletin_classe_batch_pdf',
        kwargs={'class_id': c.classe.pk, 'trimestre_id': c.trimestre.pk},
    ))
    assert trimestriel_batch.status_code == 200
    fragments = pdf.lot.call_args.args[0]
    assert len(fragments) == 1 and fragments[0] == str(c.payant.pk)

    rendu.reset_mock()
    batch_annuel_pedagogie = c.client.get(
        reverse('pedagogie:bulletin_annuel_classe_batch_pdf', kwargs={'class_id': c.classe.pk}),
        {'annee': c.annee.pk},
    )
    assert batch_annuel_pedagogie.status_code == 200
    fragments_annuels = pdf.lot.call_args.args[0]
    assert len(fragments_annuels) == 1 and fragments_annuels[0] == str(c.payant.pk)

    # Le lot annuel indépendant du module bulletins applique le même filtre.
    rendu.reset_mock()
    mocker.patch(
        'django.template.loader.render_to_string',
        side_effect=lambda _tpl, ctx, **_kwargs: str(ctx['inscription'].pk),
    )
    pdf_annuel = mocker.patch('bulletins.views.HTML')
    pdf_annuel.lot.return_value = b'%PDF-test'
    batch_annuel = c.client.get(reverse(
        'bulletins:bulletin_annuel_batch_pdf',
        kwargs={'class_id': c.classe.pk, 'annee_pk': c.annee.pk},
    ))
    assert batch_annuel.status_code == 200
    assert len(pdf_annuel.lot.call_args.args[0]) == 1
    assert str(c.payant.pk) in pdf_annuel.lot.call_args.args[0][0]
    assert str(c.impaye.pk) not in pdf_annuel.lot.call_args.args[0][0]


def test_publication_en_lot_et_lien_parent_n_exposent_pas_le_bulletin_bloque(resultats_prives):
    c = resultats_prives
    bloque = baker.make(
        'bulletins.Bulletin', inscription=c.impaye, trimestre=c.trimestre,
        est_publie=True, token_signature='token-eleve-impaye',
        token_expire_le=timezone.now() + timedelta(days=7),
    )
    route = reverse(
        'bulletins:bulletins_classe_publier',
        kwargs={'class_id': c.classe.pk, 'trimestre_id': c.trimestre.pk},
    )
    publication = c.client.post(route)
    assert publication.status_code == 302
    bloque.refresh_from_db()
    assert bloque.est_publie

    public = c.client.get(reverse(
        'bulletins:bulletin_parent_consulter', kwargs={'token': bloque.token_signature},
    ))
    assert public.status_code == 200
    contenu = public.content.decode()
    assert 'Bulletin indisponible' in contenu
    assert '19,00' not in contenu and '19.00' not in contenu

    parent = baker.make(
        'accounts.User', etablissement=c.etab, role='PARENT', must_change_password=False,
    )
    parent.eleves_lies.add(c.impaye.eleve)
    c.client.force_login(parent)
    portail = c.client.get(reverse('core:portail_parent'))
    assert portail.status_code == 200
    assert portail.context['enfants'][0]['derniere_mg'] is None
    portail_bulletins = c.client.get(reverse('core:portail_parent_bulletins'))
    assert portail_bulletins.status_code == 200
    assert portail_bulletins.context['enfants'][0]['bulletins'] == []

    from rest_framework.authtoken.models import Token
    from rest_framework.test import APIClient
    token, _ = Token.objects.get_or_create(user=parent)
    api_client = APIClient()
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    api_moyennes = api_client.get(reverse('api:eleve_moyennes', kwargs={'pk': c.impaye.eleve.pk}))
    assert api_moyennes.status_code == 200 and api_moyennes.json() == []
    api_bulletins = api_client.get(reverse('api:eleve_bulletins', kwargs={'pk': c.impaye.eleve.pk}))
    assert api_bulletins.status_code == 200 and api_bulletins.json() == []

    signature = c.client.post(reverse(
        'bulletins:bulletin_parent_signer', kwargs={'token': bloque.token_signature},
    ), {'nom_signataire': 'Parent'})
    assert signature.status_code == 302
    bloque.refresh_from_db()
    assert bloque.signe_le is None
