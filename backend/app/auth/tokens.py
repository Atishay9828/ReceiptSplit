"""
ReceiptSplit — Capability Token System

Generates, hashes, and verifies the opaque capability tokens that
authenticate creators and participants.  No JWTs, no sessions.

Token types (per Phase 1 Design §7.1):
  - Creator token:     rs_cr_<64 hex chars>  (32 bytes entropy)
  - Participant token: rs_pt_<64 hex chars>  (32 bytes entropy)
  - Invite token:      rs_inv_<64 hex chars> (32 bytes entropy)

Security properties:
  - 256-bit entropy — brute force infeasible.
  - Stored as SHA-256 hash only — raw token never persisted.
  - Constant-time comparison prevents timing attacks.
  - Prefixes are cosmetic (help debugging) and carry no trust.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from app.config import settings

# ── Token prefixes ─────────────────────────────────────────────────────────────

CREATOR_PREFIX = "rs_cr_"
PARTICIPANT_PREFIX = "rs_pt_"
INVITE_PREFIX = "rs_inv_"


# ── Generation ────────────────────────────────────────────────────────────────

def generate_creator_token() -> str:
    """
    Generates a new creator capability token.
    Returns the raw (plaintext) token — store only the hash.
    """
    return CREATOR_PREFIX + secrets.token_hex(settings.token_byte_length)


def generate_participant_token() -> str:
    """
    Generates a new participant capability token.
    Returns the raw (plaintext) token — store only the hash.
    """
    return PARTICIPANT_PREFIX + secrets.token_hex(settings.token_byte_length)


def generate_invite_token() -> str:
    """
    Generates a new invite token (embedded in share links).
    Returns the raw (plaintext) token — store only the hash.
    """
    return INVITE_PREFIX + secrets.token_hex(settings.token_byte_length)


# ── Hashing ───────────────────────────────────────────────────────────────────

def hash_token(token: str) -> str:
    """
    Returns the SHA-256 hex digest of a token.
    This is what gets stored in the database.

    The prefix is included in the hash input so that a creator token
    and a participant token with the same random bytes produce different hashes.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ── Verification ──────────────────────────────────────────────────────────────

def verify_token(raw_token: str, stored_hash: str) -> bool:
    """
    Constant-time comparison of hash(raw_token) against stored_hash.
    Prevents timing-based token oracle attacks.

    Returns True if the token matches, False otherwise.
    """
    computed = hash_token(raw_token)
    return hmac.compare_digest(computed, stored_hash)


# ── Parsing ───────────────────────────────────────────────────────────────────

def extract_bearer_token(authorization_header: str) -> str:
    """
    Extracts the raw token from an 'Authorization: Bearer <token>' header.

    Raises:
        ValueError: if the header is malformed.
    """
    parts = authorization_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Authorization header must be 'Bearer <token>'")
    token = parts[1].strip()
    if not token:
        raise ValueError("Token is empty")
    return token
