"""Notes : calcul des moyennes, bulletins, palmarès, relevés et bilans.

Jeu de données : classe 3e A, deux enseignements (Maths coef 4, Français coef 3,
barème 10), un devoir chacun au trimestre 1.
  Awa      16/20 et 8/10 (=16)  → moyenne 16,00 — rang 1
  Boubacar 10/20 et 5/10 (=10)  → moyenne 10,00 — rang 2
  Chantal   7/20 et 4/10 (=8)   → (28 + 24) / 7 = 7,43 — rang 3
  Éric     aucune note          → aucune moyenne
  Désiré   statut ABANDON       → exclu de tous les calculs
"""
import re
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
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR',
               numero_agrement_mena='2019-0123/MENAPLN')
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
        reponse = c.client.get(url)
        ctx = reponse.context
        assert ctx['nb_eleves'] == 4, 'Désiré (abandon) exclu de l’effectif'
        assert ctx['total_points_max'] == Decimal('140.00')
        assert (ctx['moy_max_classe'], ctx['moy_min_classe']) == (Decimal('16.00'), Decimal('7.43'))
        assert round(float(ctx['moy_avg_classe']), 2) == 11.14
        assert ctx['appreciation_generale'].libelle == 'Très bien'
        assert [r.appreciation.libelle for r in ctx['resultats_annotes']] == ['Très bien', 'Très bien']
        assert ctx['fiche_bulletin'] is None and 'Retards : <strong>0</strong>' in reponse.content.decode()
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
        from parametres.models import Distinction
        fiche = baker.make('bulletins.Bulletin', inscription=c.awa, trimestre=c.t1, absences_justifiees=2,
                           absences_non_justifiees=1, retards=3, appreciation_conseil='Excellent trimestre, félicitations du conseil.')
        fiche.distinctions.set(Distinction.objects.filter(code__in=['FELICITATIONS', 'TABLEAU_HONNEUR']))
        mentions = 'Mentions / distinctions :</strong> Félicitations · Tableau d&#x27;honneur'
        weasy = mocker.patch('pedagogie.views.bulletins.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'

        reponse = c.client.get(reverse('pedagogie:bulletin_pdf',
                                       kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}))
        assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
        assert 'Bulletin_OUEDRAOGO' in reponse['Content-Disposition']
        assert 'OUEDRAOGO' in _html(weasy) and 'Très bien' in _html(weasy)
        assert 'Total : 112,00&nbsp;/&nbsp;140 pts' in _html(weasy), 'points obtenus / points maximum (7 coef. × 20)'
        maths_awa = Resultat.objects.get(inscription=c.awa, enseignement=c.maths)
        assert maths_awa.note_ponderee == maths_awa.moyenne * 4, 'note pondérée = moyenne /20 × coefficient'
        note = str(maths_awa.note_ponderee).replace('.', ',')
        assert 'Note pond.' in _html(weasy) and note in _html(weasy) and '>Rang</th>' not in _html(weasy)
        # Modèle de référence : en-tête avec N° Agrément, titre, cartes, tableau des notes, signatures
        modele = ('N° Agrément : 2019-0123/MENAPLN', 'BULLETIN DE NOTES — TRIMESTRE 1 — 2026-2027',
                  'Identité de l\'élève', 'class="bul-table"', 'Statistiques de la classe', 'class="bul-sig-grid"')
        assert all(m in _html(weasy) for m in modele)
        assert 'DUPLICATA' not in _html(weasy)
        # Fiche « Saisir » imprimée : assiduité et appréciation du conseil de classe (prioritaire sur le commentaire généré)
        assiduite = ('Absences justifiées</div>\n                <div class="bul-stat-value">2 h',
                     'Absences non justifiées</div>\n                <div class="bul-stat-value">1 h',
                     'Retards</div>\n                <div class="bul-stat-value">3<')
        assert all(a in _html(weasy) for a in assiduite)
        assert 'Appréciation du conseil de classe' in _html(weasy)
        assert 'Excellent trimestre, félicitations du conseil.' in _html(weasy) and 'Excellent travail ce trimestre' not in _html(weasy)
        assert mentions in _html(weasy)
        assert _html(weasy).index('Excellent trimestre, félicitations du conseil.') < _html(weasy).index(mentions), \
            'mentions en dernière position de la carte du conseil'
        # Code QR (matricule, classe, moyenne du trimestre) dans la zone des signatures, sans légende
        qr = f'alt="QR bulletin {c.awa.eleve.matricule}"'
        assert _html(weasy).count('alt="QR bulletin ') == 1 and 'Code QR de vérification' not in _html(weasy)
        assert _html(weasy).index('class="bul-sig-grid"') < _html(weasy).index(qr)
        # Colonne Professeur élargie (24 %) aux dépens des colonnes Appréciation (14 %) et Signature (11 %)
        assert '<th style="width:14%;">Appréciation</th>' in _html(weasy)
        assert '<th style="width:24%;">Professeur</th>' in _html(weasy)
        assert '_____' not in _html(weasy), 'colonne Signature vide (pas de ligne en face des professeurs)'
        assert 'class="bul-card bul-dense"' not in _html(weasy), 'variante dense réservée aux bulletins de plus de 12 matières'
        # Pied de page : « établissement — Généré le JJ/MM/AAAA HH:MM — Document officiel — … », sans information de licence
        pied = ' — Document officiel — Toute falsification expose à des poursuites";'
        assert '@bottom-left' in _html(weasy) and ' — Généré le ' in _html(weasy) and pied in _html(weasy)
        assert 'restants' not in _html(weasy) and 'Licence ' not in _html(weasy)

        reponse = c.client.get(reverse('pedagogie:bulletin_classe_batch_pdf',
                                       kwargs={'class_id': c.classe.pk, 'trimestre_id': c.t1.pk}))
        assert reponse.status_code == 200
        # Lot = un document HTML par élève, paginés à part par HTML.lot (« Page 1 / 1 » sur chaque bulletin)
        fragments = weasy.lot.call_args.args[0]
        assert len(fragments) == 3 and all(f.count('class="bul-page"') == 1 for f in fragments)
        html = ''.join(fragments)
        assert all(nom in html for nom in ('OUEDRAOGO', 'SAWADOGO', 'ZONGO'))
        assert 'KABORE' not in html and 'TRAORE' not in html, 'sans moyenne : pas de bulletin'
        assert 'Total : 112,00&nbsp;/&nbsp;140 pts' in html and '/ 7,00' not in html, 'même notation que le bulletin individuel'
        assert 'Note pond.' in html and note in html and '>Rang</th>' not in html
        assert all(html.count(m) == 3 for m in modele), 'même modèle que le bulletin individuel, un par élève'
        assert 'page-break-after' not in html, 'un élève par document : pas de saut de page interne'
        assert all(a in html for a in assiduite) and 'Excellent trimestre, félicitations du conseil.' in html
        assert html.count('<div class="bul-stat-value">0 h</div>') == 4, 'Boubacar et Chantal sans fiche : 0 h'
        assert 'Résultats passables ce trimestre' in html, 'sans appréciation saisie : commentaire généré conservé'
        assert html.count('Mentions / distinctions :') == 1 and mentions in html, 'mentions cochées imprimées pour Awa seule'
        assert html.count('alt="QR bulletin ') == 3 and qr in html, 'un QR par élève'

        reponse = c.client.get(reverse('pedagogie:bulletin_duplicata_pdf',
                                       kwargs={'inscription_id': c.boubacar.pk, 'trimestre_id': c.t1.pk}))
        assert reponse.status_code == 200
        assert 'DUPLICATA' in _html(weasy).upper() and 'SAWADOGO' in _html(weasy)
        assert '&nbsp;/&nbsp;140 pts' in _html(weasy)
        assert 'Note pond.' in _html(weasy) and '>Rang</th>' not in _html(weasy)
        assert all(m in _html(weasy) for m in modele) and 'Duplicata officiel délivré le' in _html(weasy)
        assert 'Ce document est une reproduction du bulletin original' in _html(weasy) and 'dup-banner' not in _html(weasy)
        assert pied in _html(weasy) and 'Duplicata — Page' in _html(weasy)
        assert 'Assiduité du Trimestre 1' in _html(weasy) and html.count('Assiduité du Trimestre 1') == 3

    def test_bulletin_charge_tient_sur_une_page(self, classe_notee, mocker, settings, tmp_path):
        """Pire cas réaliste rendu par WeasyPrint : 16 matières (noms de professeurs longs), en-tête complet,
        3 sanctions, appréciation de trois lignes, 2 mentions, signataire avec titre et signature scannée
        → une page par élève."""
        import io
        import core.pdf
        from django.core.files.base import ContentFile
        from PIL import Image
        from parametres.models import Distinction, IdentiteEtablissement, TypeDocument
        from viescolaire.models import SanctionDisciplinaire
        settings.MEDIA_ROOT = tmp_path
        c = classe_notee
        IdentiteEtablissement.objects.filter(etablissement=c.etab).update(
            ville='Ouagadougou', devise='Discipline — Travail — Succès', adresse_complete='Secteur 15, Ouaga 2000',
            telephone='+226 25 36 47 58')
        devoir = baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1'), nb_meilleures_notes=0)
        matieres = ['Anglais', 'Histoire-Géographie', 'Sciences de la Vie et de la Terre', 'Physique-Chimie', 'Allemand',
                    'Éducation Physique et Sportive', 'Éducation Civique et Morale', 'Arts plastiques', 'Technologie',
                    'Informatique', 'Musique', 'Dessin', 'Arabe', 'Espagnol']
        profs = [('OUEDRAOGO', 'Abdoul Rasmané'), ('COMPAORE', 'Wendpanga Jean Benoit'), ('SAWADOGO', 'Mariam Rasmata'),
                 ('ZOUNGRANA', 'Pengdwendé Hamidou'), ('TAPSOBA', 'Kiswendsida Léonce'), ('SANKARA', 'Wendkuni Christian')]
        enseignements = [c.maths, c.francais]
        for i, nom in enumerate(matieres):
            ens = baker.make('pedagogie.Enseignement', classe=c.classe, annee_scolaire=c.annee, est_actif=True,
                             coefficient=Decimal('2'), matiere=baker.make('pedagogie.Matiere', nom=nom))
            ev = baker.make('pedagogie.Evaluation', enseignement=ens, trimestre=c.t1, type_evaluation=devoir, titre='Devoir',
                            bareme=Decimal('20'), statut='TERMINEE', date_planifiee=date(2026, 11, 5))
            for ins in (c.awa, c.boubacar, c.chantal):
                baker.make('pedagogie.Note', inscription=ins, evaluation=ev, valeur=Decimal(7 + (i * 3) % 13))
            enseignements.append(ens)
        for i, ens in enumerate(enseignements):
            nom, prenom = profs[i % len(profs)]
            ens.personnel = baker.make('personnel.MembrePersonnel', nom=nom, prenom=prenom, etablissement=c.etab)
            ens.save(update_fields=['personnel'])
        _calculer(c)
        fiche = baker.make('bulletins.Bulletin', inscription=c.awa, trimestre=c.t1, absences_justifiees=2,
                           absences_non_justifiees=1, retards=3,
                           appreciation_conseil="Trimestre globalement satisfaisant. L'élève participe activement et rend un "
                                                "travail régulier ; des efforts restent à fournir en sciences et en langues. "
                                                "Le conseil l'encourage à poursuivre sur cette voie et à consolider ses acquis.")
        fiche.distinctions.set(Distinction.objects.filter(code__in=['FELICITATIONS', 'TABLEAU_HONNEUR']))
        for j in range(3):
            baker.make('viescolaire.SanctionDisciplinaire', inscription=c.awa, trimestre=c.t1, is_active=True,
                       statut=SanctionDisciplinaire.StatutChoices.CONFIRME, date_sanction=date(2026, 11, 10 + j),
                       motif='Bavardage répété', type_sanction__libelle='Avertissement', type_sanction__code=f'AVERT{j}')
        type_doc, _ = TypeDocument.objects.get_or_create(code='BULLETIN', defaults={'nom': 'Bulletin', 'actif': True})
        membre = baker.make('personnel.MembrePersonnel', etablissement=c.etab, nom='KABORE', prenom='Salimata')
        baker.make('parametres.SignataireDocument', cycle=c.classe.cycle, type_document=type_doc, annee_scolaire=c.annee,
                   membre_personnel_id=membre.id, fonction='Le Directeur des Études',
                   titres_honorifiques=["Chevalier de l'Ordre du Mérite"], actif=True)
        tampon = io.BytesIO()
        Image.new('RGBA', (600, 220), (0, 0, 0, 0)).save(tampon, 'PNG')   # signature large : bornée à 1,1 cm de haut
        membre.signature.save('kabore.png', ContentFile(tampon.getvalue()), save=True)

        documents, sources = [], []

        class HTMLEspion(core.pdf.HTML):
            def __init__(self, *args, **kwargs):
                sources.append(kwargs.get('string', ''))
                super().__init__(*args, **kwargs)

            def render(self, *args, **kwargs):
                document = super().render(*args, **kwargs)
                documents.append(document)
                return document

        mocker.patch('pedagogie.views.bulletins.HTML', HTMLEspion)
        individuel = c.client.get(reverse('pedagogie:bulletin_pdf', kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}))
        lot = c.client.get(reverse('pedagogie:bulletin_classe_batch_pdf', kwargs={'class_id': c.classe.pk, 'trimestre_id': c.t1.pk}))
        duplicata = c.client.get(reverse('pedagogie:bulletin_duplicata_pdf', kwargs={'inscription_id': c.awa.pk, 'trimestre_id': c.t1.pk}))
        assert individuel.status_code == 200 and lot.status_code == 200 and duplicata.status_code == 200 and len(documents) == 5
        assert all(len(document.pages) == 1 for document in documents), 'chaque bulletin trimestriel (original, lot, duplicata) tient sur une page A4'
        assert all('class="bul-card bul-dense"' in html and html.count('<tr>') >= 17 for html in sources), '16 matières → variante dense'
        assert all('Chevalier de l&#x27;Ordre du Mérite' in html and 'Tableau d&#x27;honneur' in sources[0] for html in sources)
        signature = f'<div class="msig-sign"><img class="msig-img" src="{membre.signature.url}" alt=""></div><div class="msig-name">'
        assert all(html.count(signature) == 1 for html in sources), 'signature scannée entre la fonction et le nom du signataire'

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

    def test_textes_generes_en_virgule_francaise(self):
        """Les nombres des textes générés (appréciation élève, bilan de classe) s'écrivent 11,14 et non 11.14."""
        import re
        from types import SimpleNamespace
        from pedagogie.utils_ia import generer_analyse_bilan, generer_commentaire_eleve

        mg = SimpleNamespace(moyenne=Decimal('9.50'), rang=5, nb_matieres_validees=3, nb_matieres_total=7)
        texte = generer_commentaire_eleve(mg, 10, Decimal('11.14'), [])
        assert 'moyenne insuffisante de 9,50/20' in texte and 'moyenne de classe de 11,14/20 (rang 5/10)' in texte
        bilan = generer_analyse_bilan([{'cle': 'k', 'moy_classe': 12.5, 'taux': 66.666, 'moy_max': 17.5, 'moy_min': 4.2,
                                       'nb_eleves': 30, 'nb_admis': 20}])['k']
        assert 'moyenne de 12,50/20' in bilan['commentaire'] and 'taux de réussite de 66,7 %' in bilan['commentaire']
        assert 'écart de 13,3 points' in bilan['commentaire']
        assert not re.search(r'\d\.\d', texte + bilan['commentaire'] + ' '.join(bilan['recommandations']))

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
        # moyenne annuelle = moyenne des moyennes trimestrielles (ZONGO : (7,43 + 8,00) / 2 = 7,715 → 7,72)
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
        assert lignes['ZONGO']['moyenne'] == Decimal('7.72') and lignes['ZONGO']['decision'] == 'Redouble la classe'
        assert lignes['KABORE'] == {**lignes['KABORE'], 'moyenne': None, 'rang': None, 'admis': None, 'decision': '—'}
        assert 'TRAORE' not in lignes
        assert (data['nb_eleves'], data['nb_admis'], data['nb_redoublants'], data['taux_reussite']) == (5, 3, 2, 60.0)
        assert (data['moy_max'], data['moy_min'], data['moy_avg']) == (Decimal('15.00'), Decimal('7.72'), Decimal('11.93'))

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

    def test_notes_et_moyennes_affichees_avec_deux_decimales(self, classe_notee, mocker):
        """Toute note ou moyenne s'affiche avec deux décimales (16,00 — jamais 16 ni 16,0) : relevé écran,
        relevé PDF, fiche discipline, moyennes par discipline."""
        c = classe_notee
        _calculer(c)
        params = {'annee': c.annee.pk, 'classe': c.classe.pk, 'enseignement': c.francais.pk, 'periode': c.periode1.pk}
        ecran = c.client.get(reverse('pedagogie:releve_notes'), params).content.decode()
        assert re.search(r'>\s*8,00\s*<', ecran) and '<div class="rlv-note-sub">16,00/20</div>' in ecran   # 8/10 → 16/20
        assert '<span class="rlv-chip-val">16,00</span>' in ecran and '<span class="rlv-chip-val">11,33</span>' in ecran
        weasy = mocker.patch('pedagogie.views.resultats.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
        assert c.client.get(reverse('pedagogie:releve_notes_pdf'), params).status_code == 200
        pdf = _html(weasy)
        assert '<td class="note-ok">8,00</td>' in pdf and '<div class="recap-card-val">16,00<span>/20</span></div>' in pdf
        assert c.client.get(reverse('pedagogie:fiche_discipline_pdf'), params).status_code == 200
        fiche = _html(weasy)
        assert '<td class="note-ok">8,00</td>' in fiche
        assert '<div class="stat-val">16,00<span class="stat-val-unit">/20</span></div>' in fiche
        moyennes = c.client.get(reverse('pedagogie:moyennes_disciplines'),
                                {'annee': c.annee.pk, 'trimestre': c.t1.pk, 'classe': c.classe.pk}).content.decode()
        assert re.search(r'>\s*7,00\s*<', moyennes) and re.search(r'>\s*16,00\s*<', moyennes)   # ZONGO maths, OUEDRAOGO
        for html in (ecran, pdf, fiche, moyennes):   # texte affiché, hors balises, styles et scripts
            texte = re.sub(r'<[^>]+>', ' ', re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', html, flags=re.S))
            assert not re.search(r'\d,\d(?!\d)', texte), 'aucune valeur à une seule décimale'

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

    def test_releve_pdf_porte_le_signataire_configure(self, classe_notee, mocker, settings, tmp_path):
        """Le relevé de notes PDF porte le signataire configuré pour « Relevé de Notes » : fonction, signature
        scannée, NOM Prénom."""
        import io
        from django.core.files.base import ContentFile
        from PIL import Image
        from parametres.models import TypeDocument
        settings.MEDIA_ROOT = tmp_path
        c = classe_notee
        _calculer(c)
        membre = baker.make('personnel.MembrePersonnel', etablissement=c.etab, nom='Sawadogo', prenom='Awa')
        baker.make('parametres.SignataireDocument', cycle=c.classe.cycle, annee_scolaire=c.annee, actif=True,
                   type_document=TypeDocument.objects.get(code='RELEVE_NOTES'), membre_personnel_id=membre.id,
                   fonction='La Censeure')
        tampon = io.BytesIO()
        Image.new('RGBA', (300, 110), (0, 0, 0, 0)).save(tampon, 'PNG')
        membre.signature.save('censeure.png', ContentFile(tampon.getvalue()), save=True)
        weasy = mocker.patch('pedagogie.views.resultats.HTML')
        weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
        params = {'annee': c.annee.pk, 'enseignement': c.maths.pk, 'periode': c.periode1.pk}
        assert c.client.get(reverse('pedagogie:releve_notes_pdf'), params).status_code == 200
        pdf = _html(weasy)
        assert '<div class="msig-fonction">La Censeure</div>' in pdf
        assert '<div class="msig-sign"><img class="msig-img" src="/media/personnel/signatures/' in pdf
        assert '<div class="msig-name">SAWADOGO Awa</div>' in pdf

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


@pytest.mark.parametrize('gabarit', [
    'pedagogie/templates/pedagogie/pdf/partials/bulletin_trimestriel_style.html',
    'pedagogie/templates/pedagogie/pdf/bulletin_annuel.html',
    'pedagogie/templates/pedagogie/pdf/bulletin_annuel_batch.html',
])
def test_entete_du_tableau_des_notes_fond_clair_et_texte_lisible(gabarit):
    """Bulletins : l'en-tête des colonnes du tableau des notes est sur fond clair, en texte sombre et net
    (le bulletin trimestriel imprimait un bandeau noir à texte blanc de 7 pt)."""
    from pathlib import Path
    source = (Path(__file__).resolve().parents[2] / gabarit).read_text(encoding='utf-8')
    bloc = re.search(r'\.bul-table th \{(.*?)\}', source, re.S).group(1)
    regles = dict(re.findall(r'([a-z-]+)\s*:\s*([^;]+);', bloc))
    assert regles['background'] == '#ebebeb' and regles['color'] == '#111', gabarit
    assert regles['font-size'] == '7.5pt' and regles['font-weight'] == '700', gabarit
    assert 'letter-spacing' not in regles, gabarit
