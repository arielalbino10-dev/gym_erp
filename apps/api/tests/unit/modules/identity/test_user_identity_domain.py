from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.identity.domain.enums import UserIdentityStatus
from gym_erp_api.modules.identity.domain.errors import (
    InvalidIdentityFieldError,
    InvalidIdentityInvariantError,
    InvalidIdentityStateTransitionError,
)
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.shared_kernel.identifiers import new_uuid


def test_create_valid_identity_pending_verification():
    identity = UserIdentity.create(email="  Owner@Example.com  ")
    assert identity.status is UserIdentityStatus.PENDING_VERIFICATION
    assert identity.credential_version == 0
    assert identity.email_verified_at is None
    assert identity.email_normalized == "owner@example.com"
    assert identity.email.strip() == "Owner@Example.com"


def test_email_normalization_on_create():
    identity = UserIdentity.create(email="Contact@GYM.IO")
    assert identity.email_normalized == "contact@gym.io"


def test_create_rejects_invalid_email():
    with pytest.raises(InvalidIdentityFieldError):
        UserIdentity.create(email="not-an-email")


def test_allowed_status_transitions_lock_and_unlock():
    moment = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    identity = UserIdentity.create(email="a@b.co", now=moment).mark_email_verified(now=moment)
    locked = identity.transition_status(UserIdentityStatus.LOCKED, now=moment)
    assert locked.status is UserIdentityStatus.LOCKED
    restored = locked.transition_status(UserIdentityStatus.ACTIVE, now=moment)
    assert restored.status is UserIdentityStatus.ACTIVE


def test_invalid_transition_pending_to_locked():
    identity = UserIdentity.create(email="a@b.co")
    with pytest.raises(InvalidIdentityStateTransitionError):
        identity.transition_status(UserIdentityStatus.LOCKED)


def test_mark_email_verified_activates():
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    identity = UserIdentity.create(email="a@b.co", now=moment).mark_email_verified(now=moment)
    assert identity.status is UserIdentityStatus.ACTIVE
    assert identity.email_verified_at == moment


def test_active_without_verified_at_rejected_on_rehydrate():
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    uid = new_uuid()
    with pytest.raises(InvalidIdentityInvariantError):
        UserIdentity(
            user_id=uid,
            email="a@b.co",
            email_normalized="a@b.co",
            status=UserIdentityStatus.ACTIVE,
            credential_version=0,
            created_at=moment,
            updated_at=moment,
            email_verified_at=None,
        )


def test_credential_version_negative_rejected():
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    uid = new_uuid()
    with pytest.raises(InvalidIdentityFieldError):
        UserIdentity(
            user_id=uid,
            email="a@b.co",
            email_normalized="a@b.co",
            status=UserIdentityStatus.PENDING_VERIFICATION,
            credential_version=-1,
            created_at=moment,
            updated_at=moment,
        )


def test_disabled_to_active_without_verification_rejected():
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    disabled = UserIdentity.create(email="a@b.co", now=moment).transition_status(
        UserIdentityStatus.DISABLED,
        now=moment,
    )
    with pytest.raises(InvalidIdentityInvariantError):
        disabled.transition_status(UserIdentityStatus.ACTIVE, now=moment)


def test_disabled_to_active_after_verification_allowed():
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    active = UserIdentity.create(email="a@b.co", now=moment).mark_email_verified(now=moment)
    disabled = active.transition_status(UserIdentityStatus.DISABLED, now=moment)
    restored = disabled.transition_status(UserIdentityStatus.ACTIVE, now=moment)
    assert restored.status is UserIdentityStatus.ACTIVE


def test_increment_credential_version():
    moment = datetime(2026, 1, 2, tzinfo=UTC)
    identity = UserIdentity.create(email="a@b.co", now=moment)
    bumped = identity.increment_credential_version(now=moment)
    assert bumped.credential_version == 1
