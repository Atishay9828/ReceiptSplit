"""
Tests for app.auth.tokens — Token generation, hashing, and verification.
"""

from __future__ import annotations

import pytest

from app.auth.tokens import (
    CREATOR_PREFIX,
    INVITE_PREFIX,
    PARTICIPANT_PREFIX,
    extract_bearer_token,
    generate_creator_token,
    generate_invite_token,
    generate_participant_token,
    hash_token,
    verify_token,
)


@pytest.mark.unit
class TestTokenGeneration:
    def test_creator_token_has_correct_prefix(self):
        token = generate_creator_token()
        assert token.startswith(CREATOR_PREFIX)

    def test_participant_token_has_correct_prefix(self):
        token = generate_participant_token()
        assert token.startswith(PARTICIPANT_PREFIX)

    def test_invite_token_has_correct_prefix(self):
        token = generate_invite_token()
        assert token.startswith(INVITE_PREFIX)

    def test_creator_token_has_256_bit_entropy(self):
        # 32 bytes = 64 hex chars after prefix
        token = generate_creator_token()
        hex_part = token[len(CREATOR_PREFIX) :]
        assert len(hex_part) == 64

    def test_tokens_are_unique(self):
        tokens = {generate_creator_token() for _ in range(1000)}
        assert len(tokens) == 1000  # no collisions in 1000 samples

    def test_different_prefixes_produce_different_hashes(self):
        """Same random bytes but different prefix → different hash."""
        import secrets

        random_hex = secrets.token_hex(32)
        creator = f"{CREATOR_PREFIX}{random_hex}"
        participant = f"{PARTICIPANT_PREFIX}{random_hex}"
        assert hash_token(creator) != hash_token(participant)


@pytest.mark.unit
class TestTokenHashing:
    def test_hash_is_64_hex_chars(self):
        token = generate_creator_token()
        h = hash_token(token)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self):
        token = generate_creator_token()
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_different_hashes(self):
        t1 = generate_creator_token()
        t2 = generate_creator_token()
        assert hash_token(t1) != hash_token(t2)


@pytest.mark.unit
class TestTokenVerification:
    def test_correct_token_verifies(self):
        token = generate_creator_token()
        stored = hash_token(token)
        assert verify_token(token, stored) is True

    def test_wrong_token_fails(self):
        token = generate_creator_token()
        other = generate_creator_token()
        stored = hash_token(token)
        assert verify_token(other, stored) is False

    def test_empty_token_fails(self):
        token = generate_creator_token()
        stored = hash_token(token)
        assert verify_token("", stored) is False


@pytest.mark.unit
class TestExtractBearerToken:
    def test_valid_header(self):
        token = extract_bearer_token("Bearer rs_cr_abc123")
        assert token == "rs_cr_abc123"

    def test_case_insensitive_bearer(self):
        token = extract_bearer_token("bearer rs_cr_abc123")
        assert token == "rs_cr_abc123"

    def test_missing_bearer_raises(self):
        with pytest.raises(ValueError):
            extract_bearer_token("rs_cr_abc123")

    def test_empty_token_raises(self):
        with pytest.raises(ValueError):
            extract_bearer_token("Bearer ")

    def test_empty_header_raises(self):
        with pytest.raises(ValueError):
            extract_bearer_token("")
