import copy

import pytest

from gym_erp_api.infrastructure.mongo.filter_policy import (
    build_aggregation_pipeline,
    build_scoped_filter,
    prepare_insert_document,
    sanitize_update,
    sanitize_user_filter,
)
from gym_erp_api.shared_kernel.exceptions import ForbiddenMongoOperatorError, TenantScopeError
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    make_context_tenant_a,
    make_context_tenant_b,
)


def test_build_scoped_filter_isolates_tenant_a_and_b():
    ctx_a = make_context_tenant_a()
    ctx_b = make_context_tenant_b()
    filter_a = build_scoped_filter(ctx_a, {"status": "active"}, branch_scoped=False)
    filter_b = build_scoped_filter(ctx_b, {"status": "active"}, branch_scoped=False)
    assert filter_a["tenant_id"] == TENANT_A_ID
    assert filter_b["tenant_id"] == TENANT_B_ID


def test_rejects_tenant_id_in_user_filter():
    ctx = make_context_tenant_a()
    with pytest.raises(TenantScopeError):
        build_scoped_filter(ctx, {"tenant_id": TENANT_B_ID}, branch_scoped=False)


def test_rejects_or_at_root():
    with pytest.raises(ForbiddenMongoOperatorError):
        sanitize_user_filter({"$or": [{"status": "active"}]})


def test_rejects_and_and_nor_at_root():
    with pytest.raises(ForbiddenMongoOperatorError):
        sanitize_user_filter({"$and": [{"status": "active"}]})
    with pytest.raises(ForbiddenMongoOperatorError):
        sanitize_user_filter({"$nor": [{"status": "active"}]})


def test_rejects_where_and_expr():
    with pytest.raises(ForbiddenMongoOperatorError):
        sanitize_user_filter({"$where": "true"})
    with pytest.raises(ForbiddenMongoOperatorError):
        sanitize_user_filter({"$expr": {"$eq": [1, 1]}})


def test_does_not_mutate_input_filter():
    original = {"status": "active"}
    copy_before = copy.deepcopy(original)
    sanitize_user_filter(original)
    assert original == copy_before


def test_sanitize_update_rejects_pipeline():
    with pytest.raises(ForbiddenMongoOperatorError):
        sanitize_update([{"$set": {"status": "x"}}])  # type: ignore[arg-type]


def test_sanitize_update_rejects_tenant_id_in_set():
    with pytest.raises(TenantScopeError):
        sanitize_update({"$set": {"tenant_id": TENANT_B_ID}})


def test_branch_scoped_update_rejects_branch_id_change():
    with pytest.raises(TenantScopeError):
        sanitize_update({"$set": {"branch_id": BRANCH_Y_ID}}, branch_scoped=True)


def test_tenant_scoped_update_rejects_branch_id_in_set():
    with pytest.raises(TenantScopeError):
        sanitize_update({"$set": {"branch_id": BRANCH_Y_ID}}, branch_scoped=False)


def test_tenant_scoped_update_rejects_branch_id_unset():
    with pytest.raises(TenantScopeError):
        sanitize_update({"$unset": {"branch_id": ""}}, branch_scoped=False)


def test_update_rejects_dotted_branch_id_path():
    with pytest.raises(TenantScopeError):
        sanitize_update({"$set": {"profile.branch_id": BRANCH_Y_ID}})


def test_sanitize_update_rejects_replacement_document():
    with pytest.raises(TenantScopeError):
        sanitize_update({"status": "active"})


def test_prepare_insert_enforces_tenant_id():
    ctx = make_context_tenant_a()
    doc = prepare_insert_document({"name": "x"}, ctx)
    assert doc["tenant_id"] == TENANT_A_ID


def test_prepare_insert_rejects_conflicting_tenant_id():
    ctx = make_context_tenant_a()
    with pytest.raises(TenantScopeError):
        prepare_insert_document({"tenant_id": TENANT_B_ID}, ctx)


def test_branch_scoped_insert_requires_allowed_branch():
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    doc = prepare_insert_document(
        {"branch_id": BRANCH_X_ID, "name": "x"},
        ctx,
        branch_scoped=True,
    )
    assert doc["branch_id"] == BRANCH_X_ID
    with pytest.raises(TenantScopeError):
        prepare_insert_document(
            {"branch_id": BRANCH_Y_ID, "name": "y"},
            ctx,
            branch_scoped=True,
        )


def test_branch_scoped_applies_branch_in_filter():
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    scoped = build_scoped_filter(ctx, None, branch_scoped=True)
    assert scoped["tenant_id"] == TENANT_A_ID
    assert scoped["branch_id"] == {"$in": [BRANCH_X_ID]}


def test_branch_scoped_rejects_branch_id_from_caller():
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    with pytest.raises(TenantScopeError):
        build_scoped_filter(ctx, {"branch_id": BRANCH_Y_ID}, branch_scoped=True)


def test_aggregation_prepends_mandatory_match():
    ctx = make_context_tenant_a()
    pipeline = build_aggregation_pipeline(
        ctx,
        [{"$group": {"_id": "$status", "n": {"$sum": 1}}}],
        branch_scoped=False,
    )
    assert pipeline[0] == {"$match": {"tenant_id": TENANT_A_ID}}


def test_aggregation_rejects_lookup():
    ctx = make_context_tenant_a()
    with pytest.raises(ForbiddenMongoOperatorError):
        build_aggregation_pipeline(
            ctx,
            [{"$lookup": {"from": "other", "localField": "x", "foreignField": "y", "as": "z"}}],
            branch_scoped=False,
        )


def test_aggregation_rejects_function_in_project():
    ctx = make_context_tenant_a()
    with pytest.raises(ForbiddenMongoOperatorError):
        build_aggregation_pipeline(
            ctx,
            [
                {
                    "$project": {
                        "x": {"$function": {"body": "function(){}", "args": [], "lang": "js"}},
                    },
                },
            ],
            branch_scoped=False,
        )


def test_aggregation_limit_rejects_bool():
    ctx = make_context_tenant_a()
    with pytest.raises(ForbiddenMongoOperatorError):
        build_aggregation_pipeline(ctx, [{"$limit": True}], branch_scoped=False)


def test_aggregation_limit_accepts_int():
    ctx = make_context_tenant_a()
    pipeline = build_aggregation_pipeline(ctx, [{"$limit": 5}], branch_scoped=False)
    assert pipeline[1]["$limit"] == 5


def test_aggregation_rejects_system_variables_in_group():
    ctx = make_context_tenant_a()
    with pytest.raises(ForbiddenMongoOperatorError):
        build_aggregation_pipeline(
            ctx,
            [{"$group": {"_id": "$$ROOT", "n": {"$sum": 1}}}],
            branch_scoped=False,
        )


def test_build_mutation_scoped_filter_requires_business_criteria():
    from gym_erp_api.infrastructure.mongo.filter_policy import build_mutation_scoped_filter

    ctx = make_context_tenant_a()
    with pytest.raises(TenantScopeError):
        build_mutation_scoped_filter(ctx, {}, branch_scoped=False)
    scoped = build_mutation_scoped_filter(ctx, {"status": "active"}, branch_scoped=False)
    assert scoped["tenant_id"] == TENANT_A_ID
    assert scoped["status"] == "active"
