"""Configuration des matières par cycle, par niveau et par série du bac.

Priorité du coefficient / barème : enseignement > niveau + série > niveau > tout le cycle > défaut de la matière.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Enseignement, Matiere, MatiereCycle
from pedagogie.selectors import portees_cycle, rang_niveau


@pytest.fixture
def contexte(db):
    etab = baker.make('etablissements.Etablissement', code='MAT', nom='Ets Matières')
    primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRI', nom='Primaire', ordre=1, actif=True)
    secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire', ordre=2, actif=True)
    classes = {}
    for nom, niveau in [('CM2 A', 'CM2'), ('CP1 A', 'CP1'), ('CE1 A', 'CE1')]:
        classes[nom] = baker.make('parametres.Classe', etablissement=etab, cycle=primaire, nom=nom, niveau=niveau, actif=True)
    for nom, niveau, serie in [('6ème A', '6ème', ''), ('6ème B', '6ème ', ''), ('3ème A', '3ème', ''),
                               ('Tle A', 'Tle', 'A'), ('Tle D', 'Tle', 'D')]:
        classes[nom] = baker.make('parametres.Classe', etablissement=etab, cycle=secondaire, nom=nom, niveau=niveau,
                                  serie_bac=serie, actif=True)
    baker.make('parametres.Classe', etablissement=etab, cycle=secondaire, nom='4ème (fermée)', niveau='4ème', actif=False)
    math = Matiere.objects.create(code='MATH', nom='Mathématiques', coefficient=Decimal('2.00'), moy_max=Decimal('20.00'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    return {'etab': etab, 'primaire': primaire, 'secondaire': secondaire, 'classes': classes, 'math': math, 'annee': annee}


def _config(math, cycle, coefficient, niveau='', serie='', **extra):
    return MatiereCycle.objects.create(matiere=math, cycle=cycle, niveau=niveau, serie=serie,
                                       coefficient=Decimal(coefficient), **extra)


def _enseignement(math, classe, annee, **extra):
    return Enseignement.objects.create(matiere=math, classe=classe, annee_scolaire=annee, **extra)


class TestResolutionParClasse:
    def test_priorite_niveau_serie_niveau_cycle_defaut(self, contexte):
        math, sec, classes, annee = contexte['math'], contexte['secondaire'], contexte['classes'], contexte['annee']
        _config(math, sec, '3.00')                                   # tout le cycle
        _config(math, sec, '4.00', niveau='6ème')                    # niveau
        _config(math, sec, '4.50', niveau='Tle')                     # niveau (toutes séries)
        _config(math, sec, '5.00', niveau='Tle', serie='D', moy_max=Decimal('40.00'))  # niveau + série

        attendu = {'6ème A': '4.00', '6ème B': '4.00',  # « 6ème  » avec espace parasite → normalisé
                   '3ème A': '3.00', 'Tle A': '4.50', 'Tle D': '5.00', 'CM2 A': '2.00'}
        ens = {nom: _enseignement(math, classes[nom], annee) for nom in attendu}
        for nom, coeff in attendu.items():
            assert ens[nom].get_coefficient() == Decimal(coeff), nom
        assert ens['Tle D'].get_moy_max() == Decimal('40.00')
        assert ens['Tle A'].get_moy_max() == Decimal('20.00')
        # Le coefficient propre à l'enseignement reste prioritaire
        ens['Tle D'].coefficient = Decimal('1.00')
        assert ens['Tle D'].get_coefficient() == Decimal('1.00')

    def test_get_config_cycle_ignore_les_portees_niveau(self, contexte):
        math, sec = contexte['math'], contexte['secondaire']
        _config(math, sec, '4.00', niveau='6ème')
        assert math.get_config_cycle(sec) is None
        cycle = _config(math, sec, '3.00')
        assert math.get_config_cycle(sec) == cycle

    def test_portee_unique(self, contexte):
        math, sec = contexte['math'], contexte['secondaire']
        _config(math, sec, '5.00', niveau='Tle', serie='D')
        _config(math, sec, '4.00', niveau='Tle', serie='A')  # autre série : autorisé
        with pytest.raises(IntegrityError):
            _config(math, sec, '6.00', niveau='Tle', serie='D')

    def test_portees_du_cycle_ordre_pedagogique(self, contexte):
        assert portees_cycle(contexte['primaire']) == [('CP1', ''), ('CE1', ''), ('CM2', '')]
        assert portees_cycle(contexte['secondaire']) == [('6ème', ''), ('3ème', ''), ('Tle', 'A'), ('Tle', 'D')]
        # Portée configurée mais sans classe active (4ème fermée) : reste visible pour la matière
        _config(contexte['math'], contexte['secondaire'], '2.50', niveau='4ème')
        assert ('4ème', '') in portees_cycle(contexte['secondaire'], contexte['math'])
        assert [rang_niveau(n)[0] for n in ('CP1', 'CM2', 'Sixième', '6e', '3ème', '2nde', '1ère', 'Terminale')] == \
            sorted(rang_niveau(n)[0] for n in ('CP1', 'CM2', 'Sixième', '6e', '3ème', '2nde', '1ère', 'Terminale'))


@pytest.mark.django_db
class TestPageConfiguration:
    @pytest.fixture
    def client_admin(self, client):
        client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', must_change_password=False))
        return client

    def test_page_matiere_affiche_toutes_les_portees(self, client_admin, contexte):
        math, sec = contexte['math'], contexte['secondaire']
        _config(math, sec, '3.50')
        html = client_admin.get(reverse('pedagogie:matiere_update', args=[math.pk])).content.decode()

        assert 'Configuration par cycle et par niveau' in html
        for portee in ('Tout le cycle', 'CP1', 'CE1', 'CM2', '6ème', '3ème', 'Série A', 'Série D'):
            assert portee in html, portee
        assert html.index('>CP1<') < html.index('>CE1<') < html.index('>CM2<')
        assert html.index('>6ème<') < html.index('>3ème<') < html.index('Série A') < html.index('Série D')
        assert f'data-portee="{sec.pk}|Tle-D"' in html and f'data-portee="{sec.pk}|6ème"' in html
        # Décimaux non localisés dans les champs numériques (« 3,50 » rendrait le champ vide)
        assert 'value="3.50"' in html and 'value="3,50"' not in html and 'value="20"' in html
        # Les niveaux héritent du cycle : coefficient vide, valeur héritée en indication
        assert html.count('placeholder="3.50"') == 4   # 6ème, 3ème, Tle A, Tle D
        # Plus de <form> dans les lignes : envoi par les boutons HTMX ; aucun style inline
        corps = html.split('<table class="data-table cfg-table">')[1].split('</table>')[0]
        assert '<form' not in corps and 'style="' not in corps
        # 9 lignes (Primaire : cycle + 3 niveaux ; Secondaire : cycle + 4 portées) → 9 boutons ✓ + 1 corbeille
        assert corps.count('hx-include="closest tr"') == 10

    def test_enregistrement_suppression_par_portee(self, client_admin, contexte):
        math, sec = contexte['math'], contexte['secondaire']
        cycle_cfg = _config(math, sec, '3.00')
        url = reverse('pedagogie:matiere_cycle_save', args=[math.pk, sec.pk])
        base = {'moy_min': '0', 'moy_max': '20', 'heures_hebdomadaires': '4', 'est_obligatoire': 'on'}

        r = client_admin.post(url, {**base, 'niveau': 'Tle', 'serie': 'D', 'coefficient': '5'}, HTTP_HX_REQUEST='true')
        assert r.status_code == 200
        html = r.content.decode()
        assert f'data-portee="{sec.pk}|Tle-D"' in html and 'value="5"' in html and 'data-role="supprimer"' in html
        cfg = MatiereCycle.objects.get(matiere=math, cycle=sec, niveau='Tle', serie='D')
        assert (cfg.coefficient, cfg.heures_hebdomadaires) == (Decimal('5'), Decimal('4'))
        assert MatiereCycle.objects.filter(matiere=math).count() == 2  # la portée « tout le cycle » est intacte

        # Coefficient vide → suppression de cette seule portée ; la ligne réaffiche la valeur héritée
        r = client_admin.post(url, {**base, 'niveau': 'Tle', 'serie': 'D', 'coefficient': ''}, HTTP_HX_REQUEST='true')
        assert 'placeholder="3"' in r.content.decode() and 'data-role="supprimer"' not in r.content.decode()
        assert list(MatiereCycle.objects.filter(matiere=math)) == [cycle_cfg]

        # Bouton corbeille (hx-vals supprimer=1) sur la portée « tout le cycle »
        client_admin.post(url, {**base, 'niveau': '', 'serie': '', 'coefficient': '3', 'supprimer': '1'}, HTTP_HX_REQUEST='true')
        assert not MatiereCycle.objects.filter(matiere=math).exists()

        # Valeur invalide → erreur affichée, rien d'enregistré
        r = client_admin.post(url, {**base, 'niveau': '6ème', 'serie': '', 'coefficient': 'abc'}, HTTP_HX_REQUEST='true')
        assert 'input-error' in r.content.decode() and not MatiereCycle.objects.filter(matiere=math).exists()

    def test_liste_affiche_la_portee(self, client_admin, contexte):
        math, sec = contexte['math'], contexte['secondaire']
        _config(math, sec, '3.00')
        _config(math, sec, '5.00', niveau='Tle', serie='D')
        html = client_admin.get(reverse('pedagogie:matiere_list')).content.decode()
        assert 'Secondaire ×3' in html and 'Secondaire · Tle · Série D ×5' in html
