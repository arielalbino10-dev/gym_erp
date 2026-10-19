import pytest

from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)


def test_hash_is_sha256_hex():
    token = generate_opaque_session_token()
    digest = hash_session_token(token)
    assert len(digest) == 64
    assert digest.islower() or all(c in "0123456789abcdef" for c in digest)


def test_hash_rejects_empty():
    with pytest.raises(ValueError):
        hash_session_token("")
