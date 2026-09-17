import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestApiAuth:
    def test_obtenir_token_champs_manquants(self, client):
        url = reverse('api:obtenir_token')
        response = client.post(url, {}, content_type='application/json')
        assert response.status_code == 400

    def test_obtenir_token_identifiants_invalides(self, client):
        url = reverse('api:obtenir_token')
        response = client.post(
            url,
            {'username': 'inconnu', 'password': 'mauvais'},
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_obtenir_token_valide(self, client):
        user = baker.make('accounts.User')
        user.set_password('testpass123')
        user.save()
        url = reverse('api:obtenir_token')
        response = client.post(
            url,
            {'username': user.email, 'password': 'testpass123'},
            content_type='application/json',
        )
        assert response.status_code == 200
        assert 'token' in response.json()

    def test_eleves_sans_token(self, client):
        url = reverse('api:eleves_list')
        response = client.get(url)
        assert response.status_code == 401

    def test_eleves_avec_token(self, client):
        from rest_framework.authtoken.models import Token
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        token, _ = Token.objects.get_or_create(user=user)
        url = reverse('api:eleves_list')
        response = client.get(url, HTTP_AUTHORIZATION=f'Token {token.key}')
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# RBAC API (cloisonnement par rôle)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestApiRbac:
    """Cloisonnement RBAC de l'API : staff → son établissement ;
    parent → ses enfants ; élève → lui-même ; super admin → tous."""

    def _token(self, user):
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        return token.key

    def _auth(self, user):
        return {'HTTP_AUTHORIZATION': f'Token {self._token(user)}'}

    def _eleve_inscrit(self, etab):
        """Élève inscrit dans une classe de l'établissement."""
        eleve = baker.make('inscriptions.Eleve')
        annee = baker.make('parametres.AnneeScolaire',
                           etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe',
                            etablissement=etab, nom=f'6A-{str(eleve.pk)[:8]}')
        baker.make('inscriptions.Inscription',
                   eleve=eleve, annee_scolaire=annee, classe=classe)
        return eleve

    @pytest.fixture
    def etab_a(self):
        return baker.make('etablissements.Etablissement')

    @pytest.fixture
    def etab_b(self):
        return baker.make('etablissements.Etablissement')

    def test_parent_liste_uniquement_ses_enfants(self, client, etab_a):
        enfant = self._eleve_inscrit(etab_a)
        autre = self._eleve_inscrit(etab_a)
        parent = baker.make('accounts.User', role='PARENT', etablissement=etab_a)
        parent.eleves_lies.add(enfant)

        r = client.get(reverse('api:eleves_list'), **self._auth(parent))
        assert r.status_code == 200
        matricules = {e['matricule'] for e in r.json()}
        assert matricules == {enfant.matricule}

    def test_parent_detail_autre_eleve_refuse(self, client, etab_a):
        enfant = self._eleve_inscrit(etab_a)
        intrus = self._eleve_inscrit(etab_a)
        parent = baker.make('accounts.User', role='PARENT', etablissement=etab_a)
        parent.eleves_lies.add(enfant)

        # Son enfant : 200
        r = client.get(reverse('api:eleve_detail', args=[enfant.pk]),
                       **self._auth(parent))
        assert r.status_code == 200
        # Un autre élève de la même école : 404 (pas de fuite d'existence)
        r = client.get(reverse('api:eleve_detail', args=[intrus.pk]),
                       **self._auth(parent))
        assert r.status_code == 404

    def test_parent_donnees_elve_hors_perimetre(self, client, etab_a, etab_b):
        """Même test sur les sous-ressources (bulletins, paiements…)."""
        eleve_b = self._eleve_inscrit(etab_b)
        enfant_a = self._eleve_inscrit(etab_a)
        parent = baker.make('accounts.User', role='PARENT', etablissement=etab_a)
        parent.eleves_lies.add(enfant_a)
        for name, args in (
            ('api:eleve_inscriptions', [eleve_b.pk]),
            ('api:eleve_bulletins', [eleve_b.pk]),
            ('api:eleve_moyennes', [eleve_b.pk]),
            ('api:eleve_paiements', [eleve_b.pk]),
            ('api:eleve_presences', [eleve_b.pk]),
        ):
            r = client.get(reverse(name, args=args), **self._auth(parent))
            assert r.status_code == 404, name

    def test_parent_sans_enfant_refuse(self, client, etab_a):
        parent = baker.make('accounts.User', role='PARENT', etablissement=etab_a)
        r = client.get(reverse('api:eleves_list'), **self._auth(parent))
        assert r.status_code == 403

    def test_staff_perimetre_son_etablissement(self, client, etab_a, etab_b):
        eleve_a = self._eleve_inscrit(etab_a)
        eleve_b = self._eleve_inscrit(etab_b)
        staff = baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab_a)

        r = client.get(reverse('api:eleve_detail', args=[eleve_a.pk]),
                       **self._auth(staff))
        assert r.status_code == 200
        r = client.get(reverse('api:eleve_detail', args=[eleve_b.pk]),
                       **self._auth(staff))
        assert r.status_code == 404

    def test_super_admin_voit_tous(self, client, etab_a, etab_b):
        eleve_a = self._eleve_inscrit(etab_a)
        eleve_b = self._eleve_inscrit(etab_b)
        admin = baker.make('accounts.User', role='SUPER_ADMIN', etablissement=etab_a)

        r = client.get(reverse('api:eleves_list'), **self._auth(admin))
        matricules = {e['matricule'] for e in r.json()}
        assert {eleve_a.matricule, eleve_b.matricule} <= matricules


# ─────────────────────────────────────────────────────────────────────────────
# Renouvellement (rotation) des tokens API
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestApiTokenRefresh:
    """POST /api/auth/token/refresh/ : rotation du token avant expiration."""

    def _token(self, user):
        from rest_framework.authtoken.models import Token
        return Token.objects.create(user=user)

    def test_sans_token_refuse(self, client):
        r = client.post(reverse('api:renouveler_token'),
                        content_type='application/json')
        assert r.status_code == 401

    def test_rotation_invalide_ancien_token(self, client):
        from rest_framework.authtoken.models import Token
        user = baker.make('accounts.User')
        ancien = self._token(user)
        cle1 = ancien.key

        r = client.post(reverse('api:renouveler_token'),
                        HTTP_AUTHORIZATION=f'Token {cle1}')
        assert r.status_code == 200
        cle2 = r.json()['token']
        assert cle2 != cle1
        assert set(r.json()) >= {'token', 'user_id', 'username', 'role'}

        # Un seul token subsiste
        assert Token.objects.filter(user=user).count() == 1

        # L'ancien token est mort
        r = client.get(reverse('api:eleves_list'),
                       HTTP_AUTHORIZATION=f'Token {cle1}')
        assert r.status_code == 401
        # Le nouveau fonctionne
        r = client.get(reverse('api:eleves_list'),
                       HTTP_AUTHORIZATION=f'Token {cle2}')
        assert r.status_code == 200

    def test_renouvellement_glissant(self, client):
        user = baker.make('accounts.User')
        cle = self._token(user).key
        for _ in range(3):
            r = client.post(reverse('api:renouveler_token'),
                            HTTP_AUTHORIZATION=f'Token {cle}')
            assert r.status_code == 200
            cle = r.json()['token']
        r = client.get(reverse('api:eleves_list'),
                       HTTP_AUTHORIZATION=f'Token {cle}')
        assert r.status_code == 200

    def test_token_deja_expiré_non_renouvelable(self, client):
        """Un token expiré (supprimé par ExpiringTokenAuthentication)
        ne peut pas être renouvelé : 401, retour à l'authentification
        complète avec username/password."""
        from django.utils import timezone
        from rest_framework.authtoken.models import Token
        user = baker.make('accounts.User')
        token = self._token(user)
        token.created = timezone.now() - timezone.timedelta(hours=25)
        token.save()

        r = client.post(reverse('api:renouveler_token'),
                        HTTP_AUTHORIZATION=f'Token {token.key}')
        assert r.status_code == 401
        assert not Token.objects.filter(user=user).exists()
