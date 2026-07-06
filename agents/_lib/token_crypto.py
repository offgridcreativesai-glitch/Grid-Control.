"""
agents/_lib/token_crypto.py — encrypt-at-rest for brand platform tokens.

Jul 6 security fix (fable5_review gap #3.4): brands/{slug}/.env stores real
platform tokens (IG/LinkedIn/YouTube/X) in plaintext on disk. Combined with
the filesystem being the only tenancy boundary for brand files, a leaked
backup, a misconfigured Railway volume mount, or filesystem access of any
kind exposes every connected brand's live tokens directly.

Design: symmetric encryption (Fernet — AES-128-CBC + HMAC, from the
`cryptography` package) keyed by GRID_TOKEN_ENCRYPTION_KEY, an INFRA-level
env var (Railway/global .env — never brand-specific, never committed).
Encrypted values are stored as `enc:<fernet token>`; plain values (already on
disk from before this fix, or written when no key is configured yet) are
read back unchanged — this is a live migration, not a hard cutover:

  - No key configured -> encrypt() is a no-op (returns the value as-is) and
    logs a one-time warning. Nothing breaks; tokens stay plaintext until a
    key is deployed.
  - Key configured -> every new write is encrypted. Existing plaintext
    values keep working (decrypt() passes through anything without the
    `enc:` prefix) until they're next re-saved through Connections, at which
    point they get encrypted too.
  - A value that starts with `enc:` but fails to decrypt (wrong key, or the
    key rotated) returns "" for THAT field only — never raises, never lets
    one bad field crash brand_env()'s read of every other token in the file.
"""
from __future__ import annotations

import os

_PREFIX = "enc:"
_warned_no_key = False


def _get_fernet():
    """Returns a Fernet instance, or None if no key is configured."""
    key = os.getenv("GRID_TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except Exception:
        return None


def encrypt(value: str) -> str:
    """Encrypt a token for storage. No-op (plaintext) if no key is configured
    — logs once so the gap is visible in server logs, not silent forever."""
    global _warned_no_key
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        if not _warned_no_key:
            print("[token_crypto] GRID_TOKEN_ENCRYPTION_KEY not set — brand tokens "
                  "are being written in PLAINTEXT. Set it to encrypt at rest.")
            _warned_no_key = True
        return value
    return _PREFIX + f.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a stored token. Values without the enc: prefix are passed
    through unchanged (plaintext from before this fix, or no key configured).
    A value that fails to decrypt returns "" (fail-safe: never surface a
    corrupt/undecryptable blob as if it were a usable token) rather than
    raising and breaking every other token in the same brand_env() read."""
    if not value or not value.startswith(_PREFIX):
        return value
    f = _get_fernet()
    if f is None:
        return ""  # encrypted value but no key available — can't recover it
    try:
        return f.decrypt(value[len(_PREFIX):].encode()).decode()
    except Exception:
        return ""


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(_PREFIX)
