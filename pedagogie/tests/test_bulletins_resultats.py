"""Notes : calcul des moyennes, bulletins, palmarès, relevés et bilans.

Jeu de données : classe 3e A, deux enseignements (Maths coef 4, Français coef 3,
barème 10), un devoir chacun au trimestre 1.
  Awa      16/20 et 8/10 (=16)  → moyenne 16,00 — rang 1
  Boubacar 10/20 et 5/10 (=10)  → moyenne 10,00 — rang 2
  Chantal   7/20 et 4/10 (=8)   → (28 + 24) / 7 = 7,43 — rang 3
  Éric     aucune note          → aucune moyenne
  Désiré   statut ABANDON       → exclu de tous les calculs
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import MoyenneGenerale, Resultat
from pedagogie.views.bulletins import _compute_palmares_annuel, _get_mention, _match_appreciation

APPRECIATIONS = [
    ('Insuffisant', '0', '9.99'), ('Passable', '10', '11.99'), ('Assez bien', '12', '13.99'),
    ('Bien', '14', '15.99'), ('Très bien', '16', '20'),
]


def _eleve(nom, prenom):
    return baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, photo='')


@pytest.fixture
def classe_notee(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR', ville='Ouagadougou')
    user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab,
                      must_change_password=False)
    client.force_login(user)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    t1 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
                    date_debut=date(2026, 10, 1), date_fin=date(2026, 12, 20))
    t2 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=2, nom='Trimestre 2',
                    date_debut=date(2027, 1, 5), date_fin=date(2027, 3, 31))
    periode1 = baker.make('parametres.PeriodeEvaluation', etablissement=etab, annee_scolaire=annee,
                          type_periode='TRIMESTRE', nom='Trimestre 1', numero=1)
    for libelle, moy_min, moy_max in APPRECIATIONS:
        baker.make('parametres.AppreciationMoyenneSecondaire', etablissement=etab, libelle=libelle,
                   moy_min=Decimal(moy_min), moy_max=Decimal(moy_max), actif=True)

    maths = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, est_actif=True,
                       coefficient=Decimal('4'), matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'))
    francais = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, est_actif=True,
                          coefficient=Decimal('3'), matiere=baker.make('pedagogie.Matiere', nom='Français'))
    devoir = baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1'), nb_meilleures_notes=0)
    ev_maths = baker.make('pedagogie.Evaluation', enseignement=maths, trimestre=t1, type_evaluation=devoir,
                          titre='Devoir 1', bareme=Decimal('20'), statut='TERMINEE', date_planifiee=date(2026, 11, 5))
    ev_francais = baker.make('pedagogie.Evaluation', enseignement=francais, trimestre=t1, type_evaluation=devoir,
                             titre='Dictée', bareme=Decimal('10'), statut='TERMINEE', date_planifiee=date(2026, 11, 6))

    def inscrire(nom, prenom, statut='ACTIF'):
        return baker.make('inscriptions.Inscription', eleve=_eleve(nom, prenom), classe=classe,
                          annee_scolaire=annee, statut=statut)

    awa, boubacar, chantal = inscrire('OUEDRAOGO', 'Awa'), inscrire('SAWADOGO', 'Boubacar'), inscrire('ZONGO', 'Chantal')
    eric = inscrire('KABORE', 'Éric')
    desire = inscrire('TRAORE', 'Désiré', statut='ABANDON')
    for ins, n_maths, n_fr in ((awa, 16, 8), (boubacar, 10, 5), (chantal, 7, 4), (desire, 20, 10)):
        baker.make('pedagogie.Note', inscription=ins, evaluation=ev_maths, valeur=Decimal(n_maths))
        baker.make('pedagogie.Note', inscription=ins, evaluation=ev_francais, valeur=Decimal(n_fr))

    return SimpleNamespace(client=client, etab=etab, annee=annee, classe=classe, t1=t1, t2=t2, periode1=periode1,
                           maths=maths, francais=francais, awa=awa, boubacar=boubacar, chantal=chantal,
                           eric=eric, desire=desire)


def _calculer(c):
    reponse = c.client.post(reverse('pedagogie:calculer_moyennes_classe', kwargs={'class_id': c.classe.pk}),
                            {'trimestre_id': c.t1.pk})
    assert reponse.status_code == 302
    return reponse


def _html(mock):
    return mock.call_args.kwargs['string']


@pytest.mark.django_db
class TestCalculMoyennes:
    def test_moyennes_rangs_et_exclusions(self, classe_notee):
        c = classe_notee
        _calculer(c)

        mg = {m.inscription_id: m for m in MoyenneGenerale.objects.filter(trimestre=c.t1)}
        assert set(mg) == {c.awa.pk, c.boubacar.pk, c.chantal.pk}, 'ni Éric (sans note) ni Désiré (abandon)'
        assert (mg[c.awa.pk].moyenne, mg[c.awa.pk].rang) == (Decimal('16.00'), 1)
        assert (mg[c.boubacar.pk].moyenne, mg[c.boubacar.pk].rang) == (Decimal('10.00'), 2)
        assert (mg[c.chantal.pk].moyenne, mg[c.chantal.pk].rang) == (Decimal('7.43'), 3)
        assert mg[c.awa.pk].total_coefficients == Decimal('7.00')
        assert mg[c.awa.pk].total_points == Decimal('112.00')

        francais_awa = Resultat.objects.get(inscription=c.awa, enseignement=c.francais, trimestre=c.t1)
        assert francais_awa.moyenne == Decimal('16.00'), 'note 8/10 ramenée sur 20'
        assert francais_awa.coefficient_utilise == Decimal('3.00')

    def test_sans_trimestre_redirige_avec_erreur(self, classe_notee):
        c = classe_notee
        reponse = c.client.post(reverse('pedagogie:calculer_moyennes_classe', kwargs={'class_id': c.classe.pk}), {})
        assert reponse.status_code == 302
        assert MoyenneGenerale.objects.count() == 0

    def test_resultat_classe_affiche_les_moyennes(self, classe_notee):
        c = classe_notee
        _calculer(c)
        reponse = c.client.get(reverse('pedagogie:resultat_classe', kwargs={'class_id': c.classe.pk}))
        assert reponse.status_code == 200
        assert reponse.context['trimestre'] == c.t1
        assert set(reponse.context['moyennes_gen']) == {c.awa.pk, c.boubacar.pk, c.chantal.pk}
        assert c.desire not in reponse.context['inscriptions']

        reponse = c.client.get(reverse('pedagogie:resultat_classe', kwargs={'class_id': c.classe.pk}),
                               {'annee': c.annee.pk, 'trimestre': c.t2.pk})
        assert reponse.context['trimestre'] == c.t2
        assert reponse.context['moyennes_gen'] == {}

    def test_resultat_classe_sans_annee(self, client):
        client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN'))
        classe = baker.make('parametres.Classe')
        reponse = client.get(reverse('pedagogie:resultat_classe', kwargs={'class_id': classe.pk}))
        assert reponse.status_code == 200
        assert reponse.context['error'] == 'Aucune année scolaire trouvée.'


@pytest.mark.django_db
class TestBulletinTrimestriel:
    def test_apercu_contexte(self, classe_notee):
        c = classe_notee
        _calculer(c)
        url = reverse('pedagogie:bulletin_apercu', kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk})
        ctx = c.client.get(url).context
        assert ctx['nb_eleves'] == 4, 'Désiré (abandon) exclu de l’effectif'
        assert ctx['total_points_max'] == Decimal('140.00')
        assert (ctx['moy_max_classe'], ctx['moy_min_classe']) == (Decimal('16.00'), Decimal('7.43'))
        assert round(float(ctx['moy_avg_classe']), 2) == 11.14
        assert ctx['appreciation_generale'].libelle == 'Très bien'
        assert [r.appreciation.libelle for r in ctx['resultats_annotes']] == ['Très bien', 'Très bien']
        assert ctx['competences_data'] is None, 'pas de compétences APC au secondaire'
        assert ctx['date_lieu'].startswith('Ouagadougou, le ')

        url = reverse('pedagogie:bulletin_apercu', kwargs={'inscription_id': c.chantal.pk, 'trimestre_id': c.t1.pk})
        assert c.client.get(url).context['appreciation_generale'].libelle == 'Insuffisant'

    def test_boutons_pdf_de_l_apercu(self, classe_notee, mocker):
        """« Générer le PDF » / « Télécharger le PDF » pointent sur les routes réelles (trimestriel et annuel)."""
        c = classe_notee
        _calculer(c)
        weasy = mocker.patch('pedagogie.views.bulletins.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
        apercus = (
            reverse('pedagogie:bulletin_apercu', kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}),
            reverse('pedagogie:bulletin_annuel_apercu', kwargs={'inscription_id': c.awa.pk}),
        )
        for apercu in apercus:
            reponse = c.client.get(apercu)
            pdf_url = reponse.context['pdf_url']
            assert reponse.content.decode().count(f'href="{pdf_url}"') == 2
            assert c.client.get(reponse.context['retour_url']).status_code == 200
            assert c.client.get(pdf_url)['Content-Type'] == 'application/pdf'

    def test_pdf_individuel_batch_et_duplicata(self, classe_notee, mocker):
        c = classe_notee
        _calculer(c)
        weasy = mocker.patch('pedagogie.views.bulletins.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'

        reponse = c.client.get(reverse('pedagogie:bulletin_pdf',
                                       kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}))
        assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
        assert 'Bulletin_OUEDRAOGO' in reponse['Content-Disposition']
        assert 'OUEDRAOGO' in _html(weasy) and 'Très bien' in _html(weasy)

        reponse = c.client.get(reverse('pedagogie:bulletin_classe_batch_pdf',
                                       kwargs={'class_id': c.classe.pk, 'trimestre_id': c.t1.pk}))
        assert reponse.status_code == 200
        html = _html(weasy)
        assert all(nom in html for nom in ('OUEDRAOGO', 'SAWADOGO', 'ZONGO'))
        assert 'KABORE' not in html and 'TRAORE' not in html, 'sans moyenne : pas de bulletin'

        reponse = c.client.get(reverse('pedagogie:bulletin_duplicata_pdf',
                                       kwargs={'inscription_id': c.boubacar.pk, 'trimestre_id': c.t1.pk}))
        assert reponse.status_code == 200
        assert 'DUPLICATA' in _html(weasy).upper() and 'SAWADOGO' in _html(weasy)

    def test_batch_sans_moyenne_redirige(self, classe_notee, mocker):
        c = classe_notee
        mocker.patch('pedagogie.views.bulletins.HTML')
        reponse = c.client.get(reverse('pedagogie:bulletin_classe_batch_pdf',
                                       kwargs={'class_id': c.classe.pk, 'trimestre_id': c.t2.pk}))
        assert reponse.status_code == 302
        assert reponse.url == reverse('pedagogie:resultat_classe', kwargs={'class_id': c.classe.pk})


class TestFonctionsPures:
    @pytest.mark.parametrize('moyenne, mention', [
        (Decimal('16'), 'Très Bien'), (Decimal('15.99'), 'Bien'), (Decimal('14'), 'Bien'),
        (Decimal('12'), 'Assez Bien'), (Decimal('10'), 'Passable'), (Decimal('9.99'), 'Insuffisant'), (None, None),
    ])
    def test_mention(self, moyenne, mention):
        assert _get_mention(moyenne) == mention

    def test_appreciation_trou_de_configuration(self):
        bas = SimpleNamespace(libelle='Insuffisant', moy_min=Decimal('0'), moy_max=Decimal('9.99'))
        haut = SimpleNamespace(libelle='Assez bien', moy_min=Decimal('12'), moy_max=Decimal('13.99'))
        apprs = [bas, haut]
        assert _match_appreciation(Decimal('5'), apprs) is bas, 'correspondance exacte'
        assert _match_appreciation(Decimal('11'), apprs) is bas, 'trou 10–12 : borne supérieure la plus proche en dessous'
        assert _match_appreciation(Decimal('15'), apprs) is haut
        assert _match_appreciation(None, apprs) is None
        assert _match_appreciation(Decimal('11'), []) is None


@pytest.mark.django_db
class TestPalmaresAnnuel:
    @pytest.fixture
    def palmares(self, classe_notee):
        c = classe_notee
        fatou = baker.make('inscriptions.Inscription', eleve=_eleve('BARRY', 'Fatou'), classe=c.classe,
                           annee_scolaire=c.annee, statut='ACTIF')
        # Σ points / Σ coefficients sur les deux trimestres
        points = {c.awa: (112, 98), fatou: (112, 98), c.boubacar: (70, 70), c.chantal: (52, 56), c.desire: (140, 140)}
        for ins, (p1, p2) in points.items():
            baker.make('pedagogie.MoyenneGenerale', inscription=ins, trimestre=c.t1, total_points=Decimal(p1),
                       total_coefficients=Decimal('7'), moyenne=Decimal(p1) / 7)
            baker.make('pedagogie.MoyenneGenerale', inscription=ins, trimestre=c.t2, total_points=Decimal(p2),
                       total_coefficients=Decimal('7'), moyenne=Decimal(p2) / 7)
        c.fatou = fatou
        return c

    def test_calcul_rangs_ex_aequo_et_decisions(self, palmares):
        c = palmares
        data = _compute_palmares_annuel(c.classe, c.annee)
        lignes = {l['eleve'].nom: l for l in data['palmares']}
        assert [l['eleve'].nom for l in data['palmares']] == ['BARRY', 'OUEDRAOGO', 'SAWADOGO', 'ZONGO', 'KABORE']
        assert (lignes['BARRY']['rang'], lignes['OUEDRAOGO']['rang']) == (1, 1), 'ex aequo à 15,00'
        assert lignes['SAWADOGO']['rang'] == 3 and lignes['ZONGO']['rang'] == 4
        assert lignes['OUEDRAOGO']['moyenne'] == Decimal('15.00')
        assert lignes['SAWADOGO'] == {**lignes['SAWADOGO'], 'moyenne': Decimal('10.00'), 'admis': True,
                                      'decision': 'Admis(e) en classe supérieure'}
        assert lignes['ZONGO']['moyenne'] == Decimal('7.71') and lignes['ZONGO']['decision'] == 'Redouble la classe'
        assert lignes['KABORE'] == {**lignes['KABORE'], 'moyenne': None, 'rang': None, 'admis': None, 'decision': '—'}
        assert 'TRAORE' not in lignes
        assert (data['nb_eleves'], data['nb_admis'], data['nb_redoublants'], data['taux_reussite']) == (5, 3, 2, 60.0)
        assert (data['moy_max'], data['moy_min'], data['moy_avg']) == (Decimal('15.00'), Decimal('7.71'), Decimal('11.93'))

    def test_vues_html_et_pdf(self, palmares, mocker):
        c = palmares
        reponse = c.client.get(reverse('pedagogie:palmares_annuel', kwargs={'class_id': c.classe.pk}))
        assert reponse.status_code == 200
        assert reponse.context['taux_reussite'] == 60.0 and reponse.context['annee_scolaire'] == c.annee

        weasy = mocker.patch('pedagogie.views.bulletins.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
        reponse = c.client.get(reverse('pedagogie:palmares_annuel_pdf', kwargs={'class_id': c.classe.pk}),
                               {'annee': c.annee.pk})
        assert reponse.status_code == 200
        assert 'Palmares_3e A_2026-2027.pdf' in reponse['Content-Disposition']
        assert 'BARRY' in _html(weasy) and 'Redouble la classe' in _html(weasy)


@pytest.mark.django_db
class TestRelevesEtBilans:
    def test_releve_notes_bareme_moyennes_et_rangs(self, classe_notee):
        c = classe_notee
        _calculer(c)
        params = {'annee': c.annee.pk, 'classe': c.classe.pk, 'enseignement': c.francais.pk, 'periode': c.periode1.pk}
        ctx = c.client.get(reverse('pedagogie:releve_notes'), params).context
        table = {row['inscription'].eleve.nom: row for row in ctx['table']}
        assert list(table) == ['KABORE', 'OUEDRAOGO', 'SAWADOGO', 'ZONGO'], 'ordre alphabétique, abandon exclu'
        assert table['OUEDRAOGO']['notes'][0]['sur_20'] == 16.0, '8/10 → 16/20'
        assert (table['OUEDRAOGO']['rang'], table['SAWADOGO']['rang'], table['ZONGO']['rang']) == (1, 2, 3)
        assert table['KABORE']['rang'] is None and table['KABORE']['notes'] == [None]
        assert ctx['ev_stats'][0]['avg'] == 11.33 and ctx['ev_stats'][0]['count'] == 3
        assert ctx['moy_classe'] == 11.33
        assert ctx['moy_max']['inscription'] == c.awa and ctx['moy_min']['inscription'] == c.chantal
        assert (ctx['nb_saisies'], ctx['nb_max_saisies']) == (3, 4)

    def test_releve_et_fiche_pdf(self, classe_notee, mocker):
        c = classe_notee
        _calculer(c)
        weasy = mocker.patch('pedagogie.views.resultats.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
        params = {'annee': c.annee.pk, 'enseignement': c.maths.pk, 'periode': c.periode1.pk}
        for nom_url in ('pedagogie:releve_notes_pdf', 'pedagogie:fiche_discipline_pdf'):
            reponse = c.client.get(reverse(nom_url), params)
            assert reponse.status_code == 200, nom_url
            assert 'Mathématiques' in _html(weasy) and 'OUEDRAOGO' in _html(weasy)
            assert c.client.get(reverse(nom_url), {'annee': c.annee.pk}).status_code == 302, 'sans enseignement'

    def test_moyennes_disciplines(self, classe_notee, mocker):
        c = classe_notee
        _calculer(c)
        params = {'annee': c.annee.pk, 'trimestre': c.t1.pk, 'classe': c.classe.pk}
        ctx = c.client.get(reverse('pedagogie:moyennes_disciplines'), params).context
        assert [e.matiere.nom for e in ctx['enseignements']] == ['Français', 'Mathématiques']
        lignes = {l['eleve'].nom: l for l in ctx['lignes']}
        assert list(lignes) == ['KABORE', 'OUEDRAOGO', 'SAWADOGO', 'ZONGO']
        assert [r.moyenne for r in lignes['ZONGO']['resultats']] == [Decimal('8.00'), Decimal('7.00')]
        assert lignes['ZONGO']['mg'].moyenne == Decimal('7.43')
        assert lignes['KABORE']['resultats'] == [None, None] and lignes['KABORE']['mg'] is None

        partiel = c.client.get(reverse('pedagogie:moyennes_disciplines'), {**params, '_partial': 'trimestres'},
                               HTTP_HX_REQUEST='true')
        assert 'Trimestre 1' in partiel.content.decode() and 'Trimestre 2' in partiel.content.decode()

        weasy = mocker.patch('pedagogie.views.resultats.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
        assert c.client.get(reverse('pedagogie:moyennes_disciplines_pdf'), params).status_code == 200
        assert 'ZONGO' in _html(weasy)
        assert c.client.get(reverse('pedagogie:moyennes_disciplines_pdf')).status_code == 302, 'filtres incomplets'

    def test_bilan_periodes(self, classe_notee):
        c = classe_notee
        _calculer(c)
        reponse = c.client.get(reverse('pedagogie:bilan_periodes'), {'annee': c.annee.pk})
        assert reponse.status_code == 200
        periodes = {p['trimestre']: p['lignes'] for p in reponse.context['periodes_data']}
        stats = {l['classe']: l['stats'] for l in periodes[c.t1]}[c.classe]
        assert stats == {'nb_eleves': 3, 'moy_classe': 11.14, 'moy_max': 16.0, 'moy_min': 7.43,
                         'nb_admis': 2, 'taux': 66.7}
        assert c.t2 not in periodes, 'période sans moyenne : absente du bilan'

    def test_classe_result_list_compte_les_inscrits(self, classe_notee):
        c = classe_notee
        reponse = c.client.get(reverse('pedagogie:classe_result_list'))
        assert reponse.status_code == 200
        assert {cl.pk: cl.nb_eleves for cl in reponse.context['classes']}[c.classe.pk] == 4
