"""Tests for audit_package.sign (Phase 5 · PR-5c · DEC-V61-014).

Security-critical tests cover:
- Round-trip sign→verify
- Tamper detection (manifest edit / zip edit / signature edit / key swap)
- Constant-time compare actually used (hmac.compare_digest)
- Domain separation via DOMAIN_TAG
- Env var key loader: base64 + plain-text + missing
- Sidecar I/O
- Sign/verify treats dict key ordering transparently (canonical JSON)
"""

from __future__ import annotations

import base64
import hmac
from pathlib import Path
from unittest.mock import patch

import pytest

from src.audit_package import (
    DOMAIN_TAG,
    HMAC_ENV_VAR,
    HmacSecretMissing,
    get_hmac_secret_from_env,
    read_sidecar,
    serialize_zip_bytes,
    sign,
    verify,
    write_sidecar,
)
from src.audit_package.sign import _build_hmac_input


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _synthetic_manifest() -> dict:
    return {
        "schema_version": 1,
        "manifest_id": "duct_flow-sig-test",
        "generated_at": "2026-04-21T01:15:00Z",
        "git": {
            "repo_commit_sha": "1670daf0" + "0" * 32,
            "whitelist_commit_sha": "947661ef" + "0" * 32,
            "gold_standard_commit_sha": "947661ef" + "0" * 32,
        },
        "case": {
            "id": "duct_flow",
            "legacy_ids": ["fully_developed_pipe"],
            "whitelist_entry": {"id": "duct_flow", "solver": "simpleFoam"},
            "gold_standard": {"case_id": "duct_flow", "source": "Jones 1976"},
        },
        "run": {"run_id": "r1", "status": "no_run_output"},
        "measurement": {"key_quantities": {"f": 0.0185}, "comparator_verdict": "PASS", "audit_concerns": []},
        "decision_trail": [],
    }


_TEST_KEY = b"test-hmac-key-32-bytes-lengthXX!"  # 32 bytes


# ---------------------------------------------------------------------------
# Round-trip sign → verify
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_sign_produces_hex_digest(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        assert len(sig) == 64  # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in sig)

    def test_verify_returns_true_for_fresh_signature(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        assert verify(m, zb, sig, _TEST_KEY) is True

    def test_verify_case_insensitive_on_hex(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        assert verify(m, zb, sig.upper(), _TEST_KEY) is True
        assert verify(m, zb, sig.lower(), _TEST_KEY) is True

    def test_signatures_are_deterministic(self):
        """Same inputs → same signature."""
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        assert sign(m, zb, _TEST_KEY) == sign(m, zb, _TEST_KEY)

    def test_dict_key_order_independence(self):
        """Canonical JSON → reordering dict keys produces same signature."""
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig_original = sign(m, zb, _TEST_KEY)
        # Build a shuffled-key variant
        m_shuffled = {k: m[k] for k in sorted(m.keys(), reverse=True)}
        sig_shuffled = sign(m_shuffled, zb, _TEST_KEY)
        assert sig_original == sig_shuffled


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------

class TestTamperDetection:
    def test_tampered_manifest_verdict_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        # Attacker flips verdict
        m_tampered = {**m, "measurement": {**m["measurement"], "comparator_verdict": "FAIL"}}
        assert verify(m_tampered, zb, sig, _TEST_KEY) is False

    def test_tampered_manifest_key_quantity_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        m_tampered = {**m}
        m_tampered["measurement"] = {**m["measurement"], "key_quantities": {"f": 0.99}}
        assert verify(m_tampered, zb, sig, _TEST_KEY) is False

    def test_tampered_zip_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        # Flip one byte in zip
        zb_tampered = bytes([zb[0] ^ 0x01]) + zb[1:]
        assert verify(m, zb_tampered, sig, _TEST_KEY) is False

    def test_tampered_signature_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        sig_tampered = ("0" if sig[0] != "0" else "f") + sig[1:]
        assert verify(m, zb, sig_tampered, _TEST_KEY) is False

    def test_wrong_key_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        wrong_key = b"different-hmac-key-32-bytes-lenXX"
        assert verify(m, zb, sig, wrong_key) is False

    def test_empty_signature_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        assert verify(m, zb, "", _TEST_KEY) is False

    def test_empty_key_fails_verify(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        assert verify(m, zb, sig, b"") is False

    def test_malformed_signature_returns_false_not_raises(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        for bad in ("zz", "short", "not-hex-chars!@#", None):
            try:
                result = verify(m, zb, bad, _TEST_KEY) if bad else verify(m, zb, "", _TEST_KEY)
            except Exception as e:
                pytest.fail(f"verify raised on malformed signature {bad!r}: {e}")
            assert result is False


# ---------------------------------------------------------------------------
# Sign input validation
# ---------------------------------------------------------------------------

class TestSignInputValidation:
    def test_sign_rejects_empty_key(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        with pytest.raises(ValueError, match="hmac_secret must not be empty"):
            sign(m, zb, b"")


# ---------------------------------------------------------------------------
# Constant-time compare instrumentation
# ---------------------------------------------------------------------------

class TestConstantTimeCompare:
    def test_verify_uses_hmac_compare_digest(self):
        """Verify must use hmac.compare_digest, not == operator.

        Timing-side-channel attacks on hex-string compare would reveal
        the signature one byte at a time via response-time measurement.
        """
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, _TEST_KEY)
        with patch("src.audit_package.sign.hmac.compare_digest", wraps=hmac.compare_digest) as mock_cd:
            verify(m, zb, sig, _TEST_KEY)
            assert mock_cd.called, "verify() did not route through hmac.compare_digest"


# ---------------------------------------------------------------------------
# HMAC input framing
# ---------------------------------------------------------------------------

class TestHmacInputFraming:
    def test_domain_tag_prepended(self):
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        hmac_input = _build_hmac_input(m, zb)
        assert hmac_input.startswith(DOMAIN_TAG)

    def test_fixed_length_components(self):
        """DOMAIN_TAG + 32-byte manifest digest + 32-byte zip digest."""
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        hmac_input = _build_hmac_input(m, zb)
        assert len(hmac_input) == len(DOMAIN_TAG) + 32 + 32

    def test_different_manifest_produces_different_input(self):
        m1 = _synthetic_manifest()
        m2 = {**m1, "manifest_id": "different-id"}
        zb = serialize_zip_bytes(m1)
        assert _build_hmac_input(m1, zb) != _build_hmac_input(m2, zb)


# ---------------------------------------------------------------------------
# Env var key loader
# ---------------------------------------------------------------------------

class TestGetHmacSecretFromEnv:
    def test_reads_plain_text_key(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "plain-text-secret")
        assert get_hmac_secret_from_env() == b"plain-text-secret"

    def test_decodes_base64_key(self, monkeypatch):
        raw = b"binary key bytes" * 2  # 32 bytes
        monkeypatch.setenv(HMAC_ENV_VAR, base64.b64encode(raw).decode("ascii"))
        assert get_hmac_secret_from_env() == raw

    def test_plain_text_that_happens_to_parse_as_base64_is_not_misread(self, monkeypatch):
        # "hello==" is valid base64 (decodes to bytes) but also makes sense as plain.
        # Our loader will base64-decode if the string is valid base64; this behavior is
        # documented. Test: the decoded bytes should be what base64 gives.
        monkeypatch.setenv(HMAC_ENV_VAR, "aGVsbG8=")  # base64 of "hello"
        assert get_hmac_secret_from_env() == b"hello"

    def test_plain_text_with_special_chars_not_base64_decoded(self, monkeypatch):
        """Non-base64 chars → fall through to UTF-8 plain-text."""
        monkeypatch.setenv(HMAC_ENV_VAR, "secret!@#$%^")
        assert get_hmac_secret_from_env() == b"secret!@#$%^"

    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv(HMAC_ENV_VAR, raising=False)
        with pytest.raises(HmacSecretMissing) as exc_info:
            get_hmac_secret_from_env()
        assert "openssl rand" in str(exc_info.value)
        assert HMAC_ENV_VAR in str(exc_info.value)

    def test_empty_env_raises(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "")
        with pytest.raises(HmacSecretMissing):
            get_hmac_secret_from_env()

    def test_whitespace_only_env_raises(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "   \t\n ")
        with pytest.raises(HmacSecretMissing):
            get_hmac_secret_from_env()

    def test_alternate_env_var_name(self, monkeypatch):
        """Custom env var name (for testing / multi-tenant)."""
        monkeypatch.setenv("MY_KEY", "secret")
        assert get_hmac_secret_from_env(env_var="MY_KEY") == b"secret"


# ---------------------------------------------------------------------------
# Sidecar I/O
# ---------------------------------------------------------------------------

class TestSidecarIO:
    def test_roundtrip_write_then_read(self, tmp_path):
        sig = "a" * 64
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        assert read_sidecar(sig_path) == sig

    def test_write_creates_parent_dir(self, tmp_path):
        sig_path = tmp_path / "a" / "b" / "out.sig"
        write_sidecar("f" * 64, sig_path)
        assert sig_path.is_file()

    def test_write_strips_and_adds_newline(self, tmp_path):
        sig_path = tmp_path / "out.sig"
        write_sidecar("  abc123  ", sig_path)
        assert sig_path.read_text() == "abc123\n"

    def test_read_missing_returns_none(self, tmp_path):
        assert read_sidecar(tmp_path / "nonexistent.sig") is None

    def test_read_empty_returns_none(self, tmp_path):
        sig_path = tmp_path / "empty.sig"
        sig_path.write_text("   \n\n")
        assert read_sidecar(sig_path) is None


# ---------------------------------------------------------------------------
# End-to-end: sign + write sidecar + read sidecar + verify
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_full_workflow(self, tmp_path, monkeypatch):
        """Full cycle mimicking operator / CI usage."""
        monkeypatch.setenv(HMAC_ENV_VAR, base64.b64encode(b"operator-key" * 3).decode("ascii"))
        key = get_hmac_secret_from_env()
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, key)
        # Persist
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        # Consumer reads back
        loaded_sig = read_sidecar(sig_path)
        assert loaded_sig is not None
        assert verify(m, zb, loaded_sig, key) is True

    def test_sidecar_read_then_verify_detects_tamper(self, tmp_path, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "secret")
        key = get_hmac_secret_from_env()
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, key)
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        # Attacker edits the sig
        sig_path.write_text("0" * 64 + "\n")
        tampered = read_sidecar(sig_path)
        assert verify(m, zb, tampered, key) is False
