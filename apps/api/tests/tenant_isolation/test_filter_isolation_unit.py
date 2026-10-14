"""Pruebas unitarias alineadas con matriz H1-A (T-12, T-13)."""

import pytest

from gym_erp_api.infrastructure.mongo.filter_policy import build_scoped_filter
from gym_erp_api.shared_kernel.exceptions import ForbiddenMongoOperatorError, TenantScopeError
from tests.support.tenant_fixtures import TENANT_B_ID, make_context_tenant_a


def test_t12_rejects_cross_tenant_filter():
    ctx = make_context_tenant_a()
    with pytest.raises(TenantScopeError):
        build_scoped_filter(ctx, {"tenant_id": TENANT_B_ID}, branch_scoped=False)


def test_t13_rejects_or_operator():
    ctx = make_context_tenant_a()
    with pytest.raises(ForbiddenMongoOperatorError):
        build_scoped_filter(
            ctx,
            {"$or": [{"status": "active"}, {"status": "pending"}]},
            branch_scoped=False,
        )
