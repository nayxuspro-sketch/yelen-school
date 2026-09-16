"""Contrôles financiers vérifiables sans connexion PostgreSQL."""

from types import SimpleNamespace

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory

from finances.models import (
    BudgetAnnuel,
    DemandePaiementMobile,
    Depense,
    Echeancier,
    Paiement,
    Remboursement,
    StatutDepense,
)
from yelen_school.finance_middleware import FinanceAccessMiddleware


def _request(path, role='ENSEIGNANT'):
    request = RequestFactory().get(path)
    request.user = SimpleNamespace(is_authenticated=True, role=role)
    return request


def test_non_financial_role_cannot_enter_finances():
    with pytest.raises(PermissionDenied):
        FinanceAccessMiddleware(lambda request: 'allowed')(
            _request('/finances/paiements/', role='ENSEIGNANT')
        )


def test_establishment_boundary_rejects_cross_school_object():
    request = _request('/finances/paiements/', role='COMPTABLE')
    request.user.etablissement_id = 'school-a'
    inscription = SimpleNamespace(
        classe=SimpleNamespace(etablissement_id='school-b'),
    )
    from finances.views import _require_same_establishment

    with pytest.raises(PermissionDenied):
        _require_same_establishment(request, inscription)


def test_public_mobile_money_link_remains_available_without_session():
    request = _request('/finances/payer/opaque-token/', role='PARENT')
    assert FinanceAccessMiddleware(lambda request: 'allowed')(request) == 'allowed'


def test_paiement_rejects_non_positive_amount_before_database():
    paiement = Paiement(montant=0)
    with pytest.raises(ValidationError):
        paiement.save()


def test_existing_paiement_is_immutable_before_database():
    paiement = Paiement(montant=100)
    paiement._state.adding = False
    with pytest.raises(ValidationError):
        paiement.save()


def test_remboursement_rejects_non_positive_amount_before_database():
    remboursement = Remboursement(montant=0)
    with pytest.raises(ValidationError):
        remboursement.save()


@pytest.mark.parametrize(
    ('model', 'field', 'invalid_value'),
    (
        (BudgetAnnuel, 'montant_prevu', -1),
        (DemandePaiementMobile, 'montant', 0),
        (Depense, 'montant', 0),
        (Echeancier, 'montant_du', 0),
    ),
)
def test_financial_amounts_are_checked_at_model_boundary(model, field, invalid_value):
    instance = model(**{field: invalid_value})
    with pytest.raises(ValidationError):
        instance.save()


def test_validated_expense_requires_a_different_approver():
    depense = Depense(
        statut=StatutDepense.VALIDEE,
        numero_depense='DEP-TEST',
        montant=100,
        valide_par_id='00000000-0000-0000-0000-000000000001',
        saisi_par_id='00000000-0000-0000-0000-000000000001',
    )
    with pytest.raises(ValidationError):
        depense.save()
