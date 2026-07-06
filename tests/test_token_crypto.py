"""Invariant tests for encrypt-at-rest brand tokens (agents/_lib/token_crypto.py).

Jul 6 security fix (fable5_review gap #3.4: plaintext platform tokens).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._lib import token_crypto
from cryptography.fernet import Fernet


def test_no_key_configured_is_plaintext_passthrough(monkeypatch):
    monkeypatch.delenv("GRID_TOKEN_ENCRYPTION_KEY", raising=False)
    token_crypto._warned_no_key = False  # reset the one-time warning flag
    assert token_crypto.encrypt("my-secret-token") == "my-secret-token"
    assert token_crypto.decrypt("my-secret-token") == "my-secret-token"


def test_round_trip_with_key_configured(monkeypatch):
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    stored = token_crypto.encrypt("my-secret-token")
    assert stored != "my-secret-token"
    assert stored.startswith("enc:")
    assert token_crypto.decrypt(stored) == "my-secret-token"


def test_plaintext_value_still_readable_after_key_is_configured(monkeypatch):
    """Migration invariant: a token written before encryption was turned on
    must keep working — decrypt() passes through anything without the enc:
    prefix, regardless of whether a key is now configured."""
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert token_crypto.decrypt("old-plaintext-token") == "old-plaintext-token"


def test_wrong_key_fails_safe_not_open(monkeypatch):
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    stored = token_crypto.encrypt("my-secret-token")
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    # Key rotated/wrong — must return "" (unusable), never the ciphertext
    # itself and never raise and crash the caller's whole brand_env() read.
    assert token_crypto.decrypt(stored) == ""


def test_encrypted_value_with_no_key_available_returns_empty(monkeypatch):
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    stored = token_crypto.encrypt("my-secret-token")
    monkeypatch.delenv("GRID_TOKEN_ENCRYPTION_KEY", raising=False)
    assert token_crypto.decrypt(stored) == ""


def test_empty_value_passthrough(monkeypatch):
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert token_crypto.encrypt("") == ""
    assert token_crypto.decrypt("") == ""


def test_is_encrypted(monkeypatch):
    monkeypatch.setenv("GRID_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    stored = token_crypto.encrypt("my-secret-token")
    assert token_crypto.is_encrypted(stored) is True
    assert token_crypto.is_encrypted("plain-value") is False
