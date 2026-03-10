"""
Tests unitaires pour core/models.py

Vérifie la fondation du projet YELEN SCHOOL :
- BaseModel : UUID pk, timestamps, is_active, abstract, ordering
- CycleChoices : 4 cycles scolaires MENA BF
- RoleChoices : 9 rôles RBAC alignés PROMPT v3.3
"""

import uuid

from django.db import models
from django.test import TestCase

from core.models import BaseModel, CycleChoices, RoleChoices


# ──────────────────────────────────────────────
# Tests BaseModel
# ──────────────────────────────────────────────

class BaseModelTest(TestCase):
    """Tests pour la classe abstraite BaseModel."""

    def test_base_model_is_abstract(self):
        """BaseModel doit être abstraite — jamais instanciée directement."""
        self.assertTrue(BaseModel._meta.abstract)

    def test_base_model_has_uuid_pk(self):
        """Le champ id doit être un UUIDField avec primary_key=True."""
        field = BaseModel._meta.get_field('id')
        self.assertIsInstance(field, models.UUIDField)
        self.assertTrue(field.primary_key)
        self.assertEqual(field.default, uuid.uuid4)
        self.assertFalse(field.editable)

    def test_base_model_has_created_at(self):
        """created_at : DateTimeField avec auto_now_add=True."""
        field = BaseModel._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)

    def test_base_model_has_updated_at(self):
        """updated_at : DateTimeField avec auto_now=True."""
        field = BaseModel._meta.get_field('updated_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now)

    def test_base_model_has_is_active(self):
        """is_active : BooleanField avec default=True."""
        field = BaseModel._meta.get_field('is_active')
        self.assertIsInstance(field, models.BooleanField)
        self.assertTrue(field.default)

    def test_base_model_ordering(self):
        """Ordering par défaut : les plus récents en premier."""
        self.assertEqual(BaseModel._meta.ordering, ['-created_at'])


# ──────────────────────────────────────────────
# Tests CycleChoices
# ──────────────────────────────────────────────

class CycleChoicesTest(TestCase):
    """Tests pour les choix de cycles scolaires MENA BF."""

    def test_cycle_choices_count(self):
        """Il doit y avoir exactement 4 cycles."""
        self.assertEqual(len(CycleChoices.choices), 4)

    def test_cycle_choices_values(self):
        """Vérification des 4 valeurs attendues."""
        expected = {'PRESCOLAIRE', 'PRIMAIRE', 'POST_PRIMAIRE', 'SECONDAIRE'}
        actual = {c.value for c in CycleChoices}
        self.assertEqual(actual, expected)

    def test_cycle_choices_labels(self):
        """Les labels doivent être en français avec accents."""
        self.assertEqual(CycleChoices.PRESCOLAIRE.label, 'Préscolaire')
        self.assertEqual(CycleChoices.PRIMAIRE.label, 'Primaire')
        self.assertEqual(CycleChoices.POST_PRIMAIRE.label, 'Post-primaire')
        self.assertEqual(CycleChoices.SECONDAIRE.label, 'Secondaire')


# ──────────────────────────────────────────────
# Tests RoleChoices
# ──────────────────────────────────────────────

class RoleChoicesTest(TestCase):
    """Tests pour les choix de rôles RBAC."""

    def test_role_choices_count(self):
        """Il doit y avoir exactement 9 rôles."""
        self.assertEqual(len(RoleChoices.choices), 9)

    def test_role_choices_values(self):
        """Vérification des 9 valeurs attendues."""
        expected = {
            'SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR', 'AVS',
            'ENSEIGNANT', 'COMPTABLE', 'SECRETAIRE', 'PARENT', 'ELEVE',
        }
        actual = {r.value for r in RoleChoices}
        self.assertEqual(actual, expected)

    def test_role_directeur_label(self):
        """Le label Directeur doit être 'Directeur / Proviseur' (jamais Directeur/SG)."""
        self.assertEqual(RoleChoices.DIRECTEUR.label, 'Directeur / Proviseur')
        self.assertNotIn('SG', RoleChoices.DIRECTEUR.label)

    def test_role_censeur_label(self):
        """Le label Censeur doit être 'Censeur / Proviseur' (jamais Censeur/SG)."""
        self.assertEqual(RoleChoices.CENSEUR.label, 'Censeur / Proviseur')
        self.assertNotIn('SG', RoleChoices.CENSEUR.label)
