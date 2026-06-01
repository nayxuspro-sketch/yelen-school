"""
bulletins/tests/test_bulletin_annuel.py
========================================
Tests unitaires pour le bulletin annuel de notes — YELEN SCHOOL v3.4

Couverture :
  - Calcul correct de la moyenne d'une période (avec coefficients différents)
  - Calcul correct de la moyenne annuelle (= moyenne des moyennes de périodes)
  - est_admis = True si moyenne >= 10
  - est_admis = False si moyenne < 10
  - Idempotence : recalculer deux fois ne crée pas de doublon
  - Période sans notes ignorée
  - Détail JSON des matières
  - Arrondi à 2 décimales
  - Statistiques de classe vides
  - Décision admis/redouble
  - Frontière exacte à 10,00

Stack : pytest + model_bakery · PostgreSQL obligatoire (jamais SQLite)
"""

import pytest
from decimal import Decimal

from model_bakery import baker


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _creer_resultat(inscription, trimestre, matiere_nom, note, coefficient=2):
    """
    Crée un Enseignement + Resultat pour un élève à un trimestre.

    Resultat est lié à un Enseignement (qui porte la matière) et non
    directement à une Matiere — c'est le schéma réel de YELEN SCHOOL.
    """
    matiere = baker.make("pedagogie.Matiere", nom=matiere_nom)
    enseignement = baker.make(
        "pedagogie.Enseignement",
        matiere=matiere,
        classe=inscription.classe,
        annee_scolaire=inscription.annee_scolaire,
    )
    return baker.make(
        "pedagogie.Resultat",
        inscription=inscription,
        enseignement=enseignement,
        trimestre=trimestre,
        moyenne_sur_20=Decimal(str(note)),
        coefficient_utilise=Decimal(str(coefficient)),
        dispense=False,
    )


def _setup_base():
    """Crée les objets communs : année, établissement, classe, élève, inscription."""
    annee = baker.make("parametres.AnneeScolaire", libelle="2024-2025")
    etablissement = baker.make("etablissements.Etablissement", ville="Ouagadougou")
    classe = baker.make(
        "parametres.Classe",
        nom="TLE A",
        etablissement=etablissement,
    )
    eleve = baker.make(
        "inscriptions.Eleve",
        nom="TIOTION",
        prenom="Abdoullahi",
        date_naissance="2008-05-15",
        genre="M",           # champ réel du modèle Eleve
    )
    inscription = baker.make(
        "inscriptions.Inscription",
        eleve=eleve,
        classe=classe,
        annee_scolaire=annee,
        statut="actif",
        est_redoublant=False,  # champ réel du modèle Inscription
    )
    return annee, classe, eleve, inscription


def _creer_trimestres(annee):
    """Crée les 3 trimestres pour une année scolaire."""
    t1 = baker.make("pedagogie.Trimestre", nom="Trimestre 1", numero=1, annee_scolaire=annee)
    t2 = baker.make("pedagogie.Trimestre", nom="Trimestre 2", numero=2, annee_scolaire=annee)
    t3 = baker.make("pedagogie.Trimestre", nom="Trimestre 3", numero=3, annee_scolaire=annee)
    return t1, t2, t3


# ══════════════════════════════════════════════════════════════════
# 1. CALCULS DE MOYENNES
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCalculMoyennes:
    """Tests pour le calcul des moyennes par période et annuelle."""

    def test_moyenne_periode_ponderee(self):
        """
        Moyenne d'une période = Σ(note × coeff) / Σ(coeff).

        Matière 1 : note=15, coeff=3 → 45 pts
        Matière 2 : note=9,  coeff=1 → 9  pts
        Total : 54 pts / 4 coeff = 13,50
        """
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)

        _creer_resultat(inscription, t1, "Mathématiques", 15, 3)
        _creer_resultat(inscription, t1, "Français", 9, 1)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        periode1 = bulletin.donnees_json["periodes"][0]
        assert periode1["moyenne_periode"] == pytest.approx(13.50, abs=0.01)
        assert periode1["total_coefficients"] == 4
        assert periode1["total_points"] == pytest.approx(54.0, abs=0.01)

    def test_moyenne_annuelle_est_moyenne_des_periodes(self):
        """
        Moyenne annuelle = Σ(moyenne_periode) / nb_periodes — arithmétique simple.

        T1=16, T2=12, T3=14 → (16+12+14)/3 = 14,00
        """
        annee, classe, eleve, inscription = _setup_base()
        t1, t2, t3 = _creer_trimestres(annee)

        _creer_resultat(inscription, t1, "Mathématiques", 16, 2)
        _creer_resultat(inscription, t2, "Mathématiques", 12, 2)
        _creer_resultat(inscription, t3, "Mathématiques", 14, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.moyenne_annuelle == Decimal("14.00")

    def test_arrondi_deux_decimales(self):
        """La moyenne annuelle est arrondie à exactement 2 décimales."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)

        _creer_resultat(inscription, t1, "Mathématiques", 10, 3)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.moyenne_annuelle == Decimal("10.00")
        # Vérifier l'exposant du Decimal (-2 = 2 décimales)
        assert bulletin.moyenne_annuelle.as_tuple().exponent == -2

    def test_periode_sans_notes_ignoree(self):
        """Une période sans notes est ignorée — ne divise pas par plus de périodes."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, t3 = _creer_trimestres(annee)

        _creer_resultat(inscription, t1, "Mathématiques", 16, 2)
        # Trimestre 2 : pas de notes
        _creer_resultat(inscription, t3, "Mathématiques", 14, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        # (16 + 14) / 2 = 15,00 — pas /3
        assert bulletin.moyenne_annuelle == Decimal("15.00")
        assert bulletin.donnees_json["nombre_periodes"] == 2

    def test_matieres_incluses_dans_json(self):
        """Le JSON contient les matières avec nom, coefficient et note."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)

        _creer_resultat(inscription, t1, "Mathématiques", 15, 3)
        _creer_resultat(inscription, t1, "Français", 12, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        periode = bulletin.donnees_json["periodes"][0]
        # Trier par nom pour un test déterministe
        matieres = sorted(periode["matieres"], key=lambda m: m["nom"])
        assert len(matieres) == 2

        francais = matieres[0]
        maths = matieres[1]
        assert maths["nom"] == "Mathématiques"
        assert maths["coefficient"] == 3
        assert maths["note"] == pytest.approx(15.0)
        assert francais["nom"] == "Français"
        assert francais["coefficient"] == 2


# ══════════════════════════════════════════════════════════════════
# 2. DÉCISION DE PASSAGE
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDecision:
    """Tests pour est_admis et la propriété decision."""

    def test_est_admis_vrai_si_moyenne_superieure_10(self):
        """est_admis = True si moyenne > 10."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 12.5, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.est_admis is True

    def test_est_admis_vrai_si_moyenne_egale_10(self):
        """est_admis = True si moyenne == 10,00 exactement (frontière inclusive)."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 10, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.est_admis is True
        assert "Passe" in bulletin.decision

    def test_est_admis_faux_si_moyenne_inferieure_10(self):
        """est_admis = False si moyenne < 10."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 9, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.est_admis is False
        assert "Redouble" in bulletin.decision

    def test_decision_admis_texte(self):
        """La propriété decision retourne le bon texte pour un élève admis."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 12, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.decision == "Passe en classe supérieure"

    def test_decision_redouble_texte(self):
        """La propriété decision retourne le bon texte pour un élève qui redouble."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 7, 2)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.decision == "Redouble la classe"

    def test_limite_frontiere_9_99(self):
        """9,99/20 → Redouble (strictement en dessous de 10)."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        # note=9.99, coeff=1 → moy_periode=9.99 → moy_annuelle=9.99
        _creer_resultat(inscription, t1, "Mathématiques", "9.99", 1)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(inscription, annee)

        assert bulletin.est_admis is False


# ══════════════════════════════════════════════════════════════════
# 3. IDEMPOTENCE (pas de doublon)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIdempotence:
    """Tests d'idempotence : recalculer deux fois ne crée pas de doublon."""

    def test_recalcul_meme_pk(self):
        """Deux appels successifs retournent le même objet (même pk)."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 14, 2)

        from bulletins.services import calculer_bulletin_annuel
        b1 = calculer_bulletin_annuel(inscription, annee)
        b2 = calculer_bulletin_annuel(inscription, annee)

        assert b1.pk == b2.pk

    def test_recalcul_pas_de_doublon_en_base(self):
        """Un seul BulletinAnnuel existe pour (inscription, annee) après recalcul."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 14, 2)

        from bulletins.services import calculer_bulletin_annuel
        from bulletins.models import BulletinAnnuel

        calculer_bulletin_annuel(inscription, annee)
        calculer_bulletin_annuel(inscription, annee)
        calculer_bulletin_annuel(inscription, annee)  # 3 appels

        count = BulletinAnnuel.objects.filter(
            inscription=inscription,
            annee_scolaire=annee,
        ).count()
        assert count == 1

    def test_recalcul_met_a_jour_la_moyenne(self):
        """
        Si on ajoute des notes entre deux calculs, le deuxième reflète
        la nouvelle moyenne (update_or_create fonctionne).
        """
        annee, classe, eleve, inscription = _setup_base()
        t1, t2, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 8, 2)

        from bulletins.services import calculer_bulletin_annuel
        b1 = calculer_bulletin_annuel(inscription, annee)
        assert b1.est_admis is False  # 8,00 < 10

        # Ajout d'un deuxième trimestre avec une bonne note
        _creer_resultat(inscription, t2, "Mathématiques", 16, 2)
        b2 = calculer_bulletin_annuel(inscription, annee)

        # (8 + 16) / 2 = 12,00 → Admis
        assert b2.moyenne_annuelle == Decimal("12.00")
        assert b2.est_admis is True
        assert b1.pk == b2.pk  # même entrée, pas de doublon


# ══════════════════════════════════════════════════════════════════
# 4. STATISTIQUES DE CLASSE
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestStatistiquesClasse:
    """Tests pour les statistiques agrégées de classe."""

    def test_statistiques_classe_vide(self):
        """Stats nulles si aucun bulletin n'a encore été généré."""
        annee = baker.make("parametres.AnneeScolaire", libelle="2024-2025")
        etablissement = baker.make("etablissements.Etablissement")
        classe = baker.make("parametres.Classe", etablissement=etablissement)

        from bulletins.services import calculer_statistiques_classe
        stats = calculer_statistiques_classe(classe, annee)

        assert stats["effectif"] == 0
        assert stats["moyenne_max"] is None
        assert stats["moyenne_min"] is None
        assert stats["moyenne_classe"] is None

    def test_statistiques_avec_un_eleve(self):
        """Avec un seul élève, min = max = moyenne_classe = sa moyenne."""
        annee, classe, eleve, inscription = _setup_base()
        t1, _, _ = _creer_trimestres(annee)
        _creer_resultat(inscription, t1, "Mathématiques", 14, 2)

        from bulletins.services import calculer_bulletin_annuel, calculer_statistiques_classe
        calculer_bulletin_annuel(inscription, annee)

        stats = calculer_statistiques_classe(classe, annee)

        assert stats["effectif"] == 1
        assert stats["moyenne_max"] == Decimal("14.00")
        assert stats["moyenne_min"] == Decimal("14.00")