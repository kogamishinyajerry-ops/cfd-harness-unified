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
    HmacLegacyKeyWarning,
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
    """PR-5c.1 per Codex M1: explicit `base64:` / `text:` / un-prefixed.
    Un-prefixed values are UTF-8 plain-text, never heuristically base64-decoded."""

    def test_un_prefixed_treated_as_utf8_plain_text(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "plain-text-secret")
        assert get_hmac_secret_from_env() == b"plain-text-secret"

    def test_base64_prefix_decoded(self, monkeypatch):
        raw = b"binary key bytes" * 2  # 32 bytes
        monkeypatch.setenv(HMAC_ENV_VAR, "base64:" + base64.b64encode(raw).decode("ascii"))
        assert get_hmac_secret_from_env() == raw

    def test_text_prefix_utf8_encoded(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "text:dev-key-via-explicit-prefix")
        assert get_hmac_secret_from_env() == b"dev-key-via-explicit-prefix"

    def test_un_prefixed_base64_looking_string_is_literal(self, monkeypatch):
        """Critical M1 test: 'aGVsbG8=' un-prefixed → literal 8 bytes, NOT decoded."""
        monkeypatch.setenv(HMAC_ENV_VAR, "aGVsbG8=")
        # Pre-PR-5c.1 behavior: b"hello" (heuristic base64 decode)
        # Post-PR-5c.1 behavior: b"aGVsbG8=" (literal bytes, no ambiguity)
        assert get_hmac_secret_from_env() == b"aGVsbG8="

    def test_text_prefix_preserves_base64_looking_payload(self, monkeypatch):
        """`text:aGVsbG8=` → b'aGVsbG8=' literally (explicit text override)."""
        monkeypatch.setenv(HMAC_ENV_VAR, "text:aGVsbG8=")
        assert get_hmac_secret_from_env() == b"aGVsbG8="

    def test_un_prefixed_special_chars_utf8_encoded(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "secret!@#$%^")
        assert get_hmac_secret_from_env() == b"secret!@#$%^"

    def test_base64_prefix_malformed_payload_raises(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "base64:not-valid-!!!")
        with pytest.raises(HmacSecretMissing) as exc_info:
            get_hmac_secret_from_env()
        assert "base64:" in str(exc_info.value)
        assert "decode" in str(exc_info.value).lower()

    def test_base64_prefix_empty_payload_raises(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "base64:")
        with pytest.raises(HmacSecretMissing) as exc_info:
            get_hmac_secret_from_env()
        assert "empty" in str(exc_info.value).lower()

    def test_text_prefix_empty_payload_raises(self, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "text:")
        with pytest.raises(HmacSecretMissing) as exc_info:
            get_hmac_secret_from_env()
        assert "empty" in str(exc_info.value).lower()

    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv(HMAC_ENV_VAR, raising=False)
        with pytest.raises(HmacSecretMissing) as exc_info:
            get_hmac_secret_from_env()
        assert "openssl rand" in str(exc_info.value)
        assert HMAC_ENV_VAR in str(exc_info.value)
        assert "base64:" in str(exc_info.value)  # format hint

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
        monkeypatch.setenv("MY_KEY", "text:secret")
        assert get_hmac_secret_from_env(env_var="MY_KEY") == b"secret"


class TestM3LegacyMigrationWarning:
    """PR-5c.2 per Codex M3: HmacLegacyKeyWarning for un-prefixed values that
    look like plausible base64 output of a binary-key generator.

    Warning is a migration aid — pre-PR-5c.1 deployments used un-prefixed
    base64 and the heuristic decoded it; now it is taken as literal UTF-8.
    Operators must rewrite as `base64:<value>` to preserve key bytes.
    """

    def test_warns_on_unprefixed_openssl_rand_base64_output(self, monkeypatch, recwarn):
        """Simulated `openssl rand -base64 32` (44 chars, padded) → warns."""
        monkeypatch.setenv(
            HMAC_ENV_VAR,
            base64.b64encode(b"\x01" * 32).decode("ascii"),  # 44 chars, padded
        )
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 1
        msg = str(warn_list[0].message)
        assert "base64:" in msg
        assert "PR-5c.1" in msg

    def test_warns_on_short_but_plausible_binary_key(self, monkeypatch, recwarn):
        """16-byte key = 24 base64 chars (minimum threshold) → warns."""
        monkeypatch.setenv(
            HMAC_ENV_VAR,
            base64.b64encode(b"sixteen-bytes-key").decode("ascii"),  # 24 chars
        )
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 1

    def test_no_warning_when_text_prefix_used(self, monkeypatch, recwarn):
        """Explicit text: prefix → no warning even for base64-shaped payload."""
        monkeypatch.setenv(
            HMAC_ENV_VAR,
            "text:" + base64.b64encode(b"\x01" * 32).decode("ascii"),
        )
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 0

    def test_no_warning_when_base64_prefix_used(self, monkeypatch, recwarn):
        """Explicit base64: prefix → no warning."""
        monkeypatch.setenv(
            HMAC_ENV_VAR,
            "base64:" + base64.b64encode(b"\x01" * 32).decode("ascii"),
        )
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 0

    def test_no_warning_on_short_plain_text(self, monkeypatch, recwarn):
        """Short plain passwords don't satisfy the ≥24-char + valid-base64 probe."""
        monkeypatch.setenv(HMAC_ENV_VAR, "dev-secret")
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 0

    def test_no_warning_on_plain_with_special_chars(self, monkeypatch, recwarn):
        """Special chars (not in base64 alphabet) → no warning."""
        monkeypatch.setenv(HMAC_ENV_VAR, "my-super-secret-key-with-dashes-!@#")
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 0

    def test_no_warning_on_urlsafe_base64(self, monkeypatch, recwarn):
        """URL-safe base64 uses - and _, not in standard alphabet → no warning."""
        # urlsafe_b64encode of 32 random bytes likely contains - or _
        urlsafe = base64.urlsafe_b64encode(b"\xff" * 32).decode("ascii")
        # Only warn if this happens to contain - or _ (most do)
        if "-" in urlsafe or "_" in urlsafe:
            monkeypatch.setenv(HMAC_ENV_VAR, urlsafe)
            get_hmac_secret_from_env()
            warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
            assert len(warn_list) == 0

    def test_warning_detects_unpadded_rejected(self, monkeypatch, recwarn):
        """Unpadded base64 (not length % 4 == 0) → no warning (would fail probe)."""
        monkeypatch.setenv(HMAC_ENV_VAR, "abcdefghij")  # 10 chars, not % 4
        get_hmac_secret_from_env()
        warn_list = [w for w in recwarn if issubclass(w.category, HmacLegacyKeyWarning)]
        assert len(warn_list) == 0


# ---------------------------------------------------------------------------
# Sidecar I/O
# ---------------------------------------------------------------------------

class TestSidecarIO:
    """PR-5c.1 per Codex L1: strict hex-shape validation on write + read."""

    def test_roundtrip_write_then_read(self, tmp_path):
        sig = "a" * 64  # valid hex
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        assert read_sidecar(sig_path) == sig

    def test_roundtrip_uppercase_hex_preserved(self, tmp_path):
        sig = "ABCDEF0123456789" * 4  # 64 chars, all valid hex
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        assert read_sidecar(sig_path) == sig

    def test_write_creates_parent_dir(self, tmp_path):
        sig_path = tmp_path / "a" / "b" / "out.sig"
        write_sidecar("f" * 64, sig_path)
        assert sig_path.is_file()

    def test_write_strips_and_adds_newline(self, tmp_path):
        sig_path = tmp_path / "out.sig"
        sig = "f" * 64
        write_sidecar(f"  {sig}  ", sig_path)
        assert sig_path.read_text() == sig + "\n"

    def test_write_rejects_empty(self, tmp_path):
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar("", tmp_path / "out.sig")

    def test_write_rejects_wrong_length(self, tmp_path):
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar("abc123", tmp_path / "out.sig")
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar("a" * 63, tmp_path / "out.sig")
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar("a" * 65, tmp_path / "out.sig")

    def test_write_rejects_non_hex_chars(self, tmp_path):
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar("g" * 64, tmp_path / "out.sig")
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar("a" * 63 + "!", tmp_path / "out.sig")

    def test_write_rejects_multiline_even_if_hex(self, tmp_path):
        # Multi-line content fails match (regex has no MULTILINE flag).
        sig_with_newline = "a" * 63 + "\na"
        with pytest.raises(ValueError, match="64 hex chars"):
            write_sidecar(sig_with_newline, tmp_path / "out.sig")

    def test_read_missing_returns_none(self, tmp_path):
        assert read_sidecar(tmp_path / "nonexistent.sig") is None

    def test_read_empty_returns_none(self, tmp_path):
        sig_path = tmp_path / "empty.sig"
        sig_path.write_text("   \n\n")
        assert read_sidecar(sig_path) is None

    def test_read_malformed_returns_none(self, tmp_path):
        """Non-hex / wrong length / multiline files → None (not raise)."""
        for bad in (
            "g" * 64,           # non-hex
            "a" * 63,           # short
            "a" * 65,           # long
            "abc123",           # way short
            "a" * 32 + "\n" + "b" * 32,  # multi-line even if all hex
        ):
            sig_path = tmp_path / "bad.sig"
            sig_path.write_text(bad)
            assert read_sidecar(sig_path) is None, f"expected None for {bad!r}"

    def test_read_tolerates_crlf_line_endings(self, tmp_path):
        """Windows CRLF after the hex digest → accepted (strip handles it)."""
        sig = "c" * 64
        sig_path = tmp_path / "crlf.sig"
        sig_path.write_bytes((sig + "\r\n").encode("ascii"))
        assert read_sidecar(sig_path) == sig

    def test_read_rejects_bom_prefix(self, tmp_path):
        """UTF-8 BOM before hex → regex fails → None (not bypass)."""
        sig = "d" * 64
        sig_path = tmp_path / "bom.sig"
        sig_path.write_bytes(b"\xef\xbb\xbf" + sig.encode("ascii"))
        assert read_sidecar(sig_path) is None

    def test_read_tolerates_trailing_whitespace(self, tmp_path):
        """Trailing spaces/tabs stripped before regex match."""
        sig = "e" * 64
        sig_path = tmp_path / "ws.sig"
        sig_path.write_text(sig + "   \t \n")
        assert read_sidecar(sig_path) == sig


# ---------------------------------------------------------------------------
# End-to-end: sign + write sidecar + read sidecar + verify
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_full_workflow_with_base64_prefix(self, tmp_path, monkeypatch):
        """Full cycle mimicking operator using explicit base64: prefix."""
        monkeypatch.setenv(
            HMAC_ENV_VAR,
            "base64:" + base64.b64encode(b"operator-key" * 3).decode("ascii"),
        )
        key = get_hmac_secret_from_env()
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, key)
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        loaded_sig = read_sidecar(sig_path)
        assert loaded_sig is not None
        assert verify(m, zb, loaded_sig, key) is True

    def test_full_workflow_with_text_prefix(self, tmp_path, monkeypatch):
        """Dev workflow with explicit text: prefix."""
        monkeypatch.setenv(HMAC_ENV_VAR, "text:dev-secret")
        key = get_hmac_secret_from_env()
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, key)
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        assert verify(m, zb, read_sidecar(sig_path), key) is True

    def test_full_workflow_un_prefixed_utf8(self, tmp_path, monkeypatch):
        """Un-prefixed env var → literal UTF-8 bytes (no base64 heuristic)."""
        monkeypatch.setenv(HMAC_ENV_VAR, "plain-dev-secret")
        key = get_hmac_secret_from_env()
        assert key == b"plain-dev-secret"
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, key)
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        assert verify(m, zb, read_sidecar(sig_path), key) is True

    def test_sidecar_read_then_verify_detects_tamper(self, tmp_path, monkeypatch):
        monkeypatch.setenv(HMAC_ENV_VAR, "secret")
        key = get_hmac_secret_from_env()
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig = sign(m, zb, key)
        sig_path = tmp_path / "bundle.zip.sig"
        write_sidecar(sig, sig_path)
        # Attacker overwrites with valid-shape but wrong content
        sig_path.write_text("0" * 64 + "\n")
        tampered = read_sidecar(sig_path)
        assert verify(m, zb, tampered, key) is False

    def test_sidecar_malformed_blocks_verify(self, tmp_path, monkeypatch):
        """PR-5c.1 L1: a malformed sidecar now returns None, not garbage."""
        monkeypatch.setenv(HMAC_ENV_VAR, "secret")
        key = get_hmac_secret_from_env()
        m = _synthetic_manifest()
        zb = serialize_zip_bytes(m)
        sig_path = tmp_path / "malformed.sig"
        sig_path.write_text("not-a-valid-signature\n")
        loaded = read_sidecar(sig_path)
        assert loaded is None
        # verify() must reject None / empty signatures
        assert verify(m, zb, loaded or "", key) is False
