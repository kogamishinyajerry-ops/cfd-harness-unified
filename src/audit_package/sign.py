"""HMAC-SHA256 signing + verification for audit-package bundles
(Phase 5 · PR-5c · DEC-V61-014).

⚠️ UPGRADE NOTE FROM PR-5c → PR-5c.1 (DEC-V61-015, Codex M3)
------------------------------------------------------------
If your pre-PR-5c.1 deployment used ``CFD_HARNESS_HMAC_SECRET`` set to
a **bare base64 string without any prefix** (e.g., ``aGVsbG8=``, or the
output of ``openssl rand -base64 32``), PR-5c.1 will reinterpret that
same value as literal UTF-8 bytes instead of base64-decoding it. New
signatures produced after the upgrade will therefore NOT match the old
key — verification of freshly signed bundles against your existing
key material will silently diverge.

To preserve the pre-upgrade signing key bytes, rewrite the env var as::

    CFD_HARNESS_HMAC_SECRET="base64:<same-value-you-previously-had>"

PR-5c.2 (DEC-V61-016, this change) adds a runtime DeprecationWarning
that fires when an un-prefixed value looks like plausible binary-key
base64 (length ≥24 chars, base64 alphabet, valid padding). Operators
will see the warning at first signer startup and can migrate without
downstream signature divergence. Use an explicit ``text:`` prefix to
suppress the warning when the key truly is plain text.

Signing domain
--------------
An audit-package signature binds together **two** artifacts:

1. The manifest dict (canonical JSON form from :mod:`audit_package.serialize`).
2. The zip bytes (byte-reproducible from :func:`serialize_zip_bytes`).

Both must agree at verify time or the signature fails. This prevents three
classes of tampering:

- Manifest edited in place (e.g., swap a verdict "FAIL" → "PASS").
- Zip contents edited (e.g., replace solver log).
- Signature transplanted from a different bundle.

Signing input framing
---------------------
Rather than concatenating the raw bytes (which would be ambiguous about
component boundaries), we HMAC over a fixed-length composition:

    hmac_input = DOMAIN_TAG || sha256(canonical_manifest_bytes) || sha256(zip_bytes)

Where ``DOMAIN_TAG = b"cfd-harness-audit-v1|"``. The DOMAIN_TAG provides
domain separation — the same key used in a different context (if ever) cannot
produce a collision with this audit-package signature. The two SHA-256
prefixes are fixed 32 bytes each, so component boundaries are unambiguous.

This structure is standard practice for multi-component MACs and avoids
length-extension / concatenation-collision ambiguity.

Key management
--------------
The HMAC secret is read from the environment variable
``CFD_HARNESS_HMAC_SECRET``. The value MUST use one of the explicit
encoding prefixes (PR-5c.1 per Codex M1 — resolves base64-vs-plain
ambiguity that could desynchronize signer and external verifiers):

- ``base64:<padded-standard-base64>`` — for high-entropy binary keys.
  Generate via ``openssl rand -base64 32`` and set as
  ``CFD_HARNESS_HMAC_SECRET="base64:<output>"``.
- ``text:<utf-8-string>`` — for ad-hoc / dev keys.
- **un-prefixed** — treated as ``text:`` (UTF-8 plain). Deliberately
  non-ambiguous: a user-visible string is always its literal bytes.

If the prefix is malformed or the value is empty, :class:`HmacSecretMissing`
is raised with an install/rotation hint. **A secret is never written to
stdout, logs, or manifests.**

Rotation procedure (documented for ops):

1. Generate new random key: ``openssl rand -base64 32``
2. Set new env var as ``CFD_HARNESS_HMAC_SECRET="base64:<new-key>"`` for
   the signer service (e.g., UI backend).
3. Previously-signed bundles remain verifiable by whoever holds the **old**
   key — sidecars don't bind to a specific key ID in v1. If per-key rotation
   tracking is required, upgrade to a key-id sidecar field in a future DEC
   (Codex M2 follow-up).
4. New bundles will sign with the new key.

Constant-time compare
---------------------
:func:`verify` uses :func:`hmac.compare_digest` for the final equality check,
preventing timing side-channels on the hex-digest compare.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import re
import warnings
from pathlib import Path
from typing import Any, Dict, Optional

from .serialize import _canonical_json

HMAC_ENV_VAR = "CFD_HARNESS_HMAC_SECRET"
DOMAIN_TAG = b"cfd-harness-audit-v1|"
_HASH_ALGO = hashlib.sha256

# PR-5c.1 per Codex L1: sidecar .sig files must contain exactly 64 lowercase
# or uppercase hex chars. Stricter validation fails fast at write + read
# boundaries instead of deferring to verify().
_HEX_SIG_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# PR-5c.1 per Codex M1: explicit encoding prefixes for CFD_HARNESS_HMAC_SECRET.
# Un-prefixed values are UTF-8 plain text (no heuristic base64 decode).
_ENV_PREFIX_BASE64 = "base64:"
_ENV_PREFIX_TEXT = "text:"

# PR-5c.2 per Codex M3: detect un-prefixed values that look like they were
# intended as base64 binary keys. 24+ base64 alphabet chars with valid padding
# is extremely unlikely for a human-chosen plain text password but typical for
# 16-byte+ random binary keys. On match, emit DeprecationWarning so operators
# upgrading from PR-5c catch the migration hazard at first signer startup.
_LEGACY_BASE64_PROBE = re.compile(r"^[A-Za-z0-9+/]{22,}={0,2}$")
_LEGACY_BASE64_MIN_LEN = 24  # base64 of 16 random bytes → 24 chars incl. padding


def _looks_like_legacy_base64(raw: str) -> bool:
    """Heuristic for Codex M3 migration warning.

    True when ``raw``:
    - has length ≥ 24 (would decode to ≥16 bytes — plausible binary key)
    - uses only standard base64 alphabet (no URL-safe chars) + ``=`` padding
    - length is a multiple of 4 (valid base64 framing)
    - actually decodes without error

    Plain-text passwords almost never satisfy all four; output of ``openssl
    rand -base64 32`` always does. The warning is a false-positive on
    dense-alphabet plain-text keys, but operators can silence it by
    switching to an explicit ``text:`` prefix.
    """
    if len(raw) < _LEGACY_BASE64_MIN_LEN or len(raw) % 4 != 0:
        return False
    if not _LEGACY_BASE64_PROBE.match(raw):
        return False
    try:
        base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return False
    return True


class HmacSecretMissing(RuntimeError):
    """The ``CFD_HARNESS_HMAC_SECRET`` environment variable is unset/empty.

    Carries an actionable rotation-procedure hint so the caller (UI,
    CI, operator) can fix it without hunting through docs.
    """


# ---------------------------------------------------------------------------
# Key loader
# ---------------------------------------------------------------------------

def get_hmac_secret_from_env(env_var: str = HMAC_ENV_VAR) -> bytes:
    """Read the HMAC secret from the environment with an explicit encoding prefix.

    Value format (PR-5c.1 per Codex M1):

    - ``base64:<padded-standard-base64>`` → base64-decoded to bytes.
    - ``text:<utf-8-string>`` → UTF-8-encoded to bytes.
    - un-prefixed → treated as UTF-8 plain text (no heuristic base64 decode).

    This eliminates the base64-vs-plain ambiguity that the prior heuristic
    could introduce between the signer and any future external (bash/Go/
    Rust) verifier.

    Raises
    ------
    HmacSecretMissing
        When the env var is unset, whitespace-only, or has a malformed
        ``base64:`` payload. The error message includes an actionable
        rotation hint.
    """
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        raise HmacSecretMissing(
            f"{env_var} is not set. Generate a fresh key with "
            "`openssl rand -base64 32` and export as "
            f'`{env_var}="base64:<output>"` (or `text:<string>` for plain-text '
            "dev keys). Un-prefixed values are treated as UTF-8 plain. See "
            "src/audit_package/sign.py module docstring for the rotation procedure."
        )

    if raw.startswith(_ENV_PREFIX_BASE64):
        payload = raw[len(_ENV_PREFIX_BASE64):]
        try:
            decoded = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as e:
            raise HmacSecretMissing(
                f"{env_var} has `base64:` prefix but payload failed to decode: {e}. "
                "Ensure the payload is padded standard base64 (try "
                "`openssl rand -base64 32` for a fresh 256-bit key)."
            )
        if not decoded:
            raise HmacSecretMissing(
                f"{env_var} has `base64:` prefix but decoded payload is empty."
            )
        return decoded

    if raw.startswith(_ENV_PREFIX_TEXT):
        payload = raw[len(_ENV_PREFIX_TEXT):]
        if not payload:
            raise HmacSecretMissing(
                f"{env_var} has `text:` prefix but payload is empty."
            )
        return payload.encode("utf-8")

    # PR-5c.2 per Codex M3: warn if un-prefixed value looks like the base64
    # output of a binary-key generator (openssl rand -base64 32). Pre-PR-5c.1
    # deployments used un-prefixed base64 and the heuristic decoded it; now
    # it is taken as literal UTF-8 bytes. Warning is at DeprecationWarning
    # level (non-fatal) so ops can see the hazard at first signer startup.
    if _looks_like_legacy_base64(raw):
        warnings.warn(
            (
                f"{env_var} appears to hold an un-prefixed base64 string. "
                f"PR-5c.1 treats this as literal UTF-8 bytes, not decoded bytes. "
                f"If you upgraded from PR-5c, your new signatures will NOT match "
                f"the pre-upgrade key. Rewrite the value as "
                f'`{env_var}="base64:<same-value>"` to preserve binary-key bytes, '
                f"or use `text:<value>` prefix to suppress this warning when the "
                f"key truly is plain text."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

    # Un-prefixed → literal UTF-8 bytes. No heuristic base64 decode.
    return raw.encode("utf-8")


# ---------------------------------------------------------------------------
# Signing primitives
# ---------------------------------------------------------------------------

def _build_hmac_input(manifest: Dict[str, Any], zip_bytes: bytes) -> bytes:
    """Construct the HMAC input: DOMAIN_TAG || sha256(manifest) || sha256(zip).

    Each SHA-256 digest is fixed 32 bytes → unambiguous component
    boundaries. DOMAIN_TAG provides domain separation from any other HMAC
    use of the same key.
    """
    manifest_bytes = _canonical_json(manifest)
    manifest_digest = _HASH_ALGO(manifest_bytes).digest()
    zip_digest = _HASH_ALGO(zip_bytes).digest()
    return DOMAIN_TAG + manifest_digest + zip_digest


def sign(
    manifest: Dict[str, Any],
    zip_bytes: bytes,
    hmac_secret: bytes,
) -> str:
    """Produce a hex-encoded HMAC-SHA256 signature.

    Parameters
    ----------
    manifest
        The manifest dict from :func:`build_manifest`. Canonicalized
        internally via :func:`_canonical_json` so dict key order does not
        affect the signature.
    zip_bytes
        The byte-reproducible zip from :func:`serialize_zip_bytes`.
    hmac_secret
        The HMAC key as bytes. Typically obtained via
        :func:`get_hmac_secret_from_env`.

    Returns
    -------
    str
        Lowercase hex digest (64 chars for SHA-256). Safe to embed in a
        sidecar `.sig` file or REST response.

    Raises
    ------
    ValueError
        If ``hmac_secret`` is empty (an empty key would produce a signature
        that's trivially forgeable).
    """
    if not hmac_secret:
        raise ValueError("hmac_secret must not be empty")
    hmac_input = _build_hmac_input(manifest, zip_bytes)
    return hmac.new(hmac_secret, hmac_input, _HASH_ALGO).hexdigest()


def verify(
    manifest: Dict[str, Any],
    zip_bytes: bytes,
    signature: str,
    hmac_secret: bytes,
) -> bool:
    """Constant-time verification of a signature.

    Parameters
    ----------
    manifest, zip_bytes, hmac_secret
        Same as :func:`sign`. If either the manifest dict contents or the
        zip bytes were tampered post-sign, this returns ``False``.
    signature
        The hex digest produced by :func:`sign`. Case-insensitive compare.

    Returns
    -------
    bool
        True iff the signature matches the reconstructed HMAC for the
        provided manifest + zip + key. False for any mismatch (tampering,
        wrong key, malformed signature).
    """
    if not hmac_secret or not signature:
        return False
    try:
        expected = sign(manifest, zip_bytes, hmac_secret)
    except ValueError:
        return False
    # Normalize case before constant-time compare. compare_digest is
    # length-stable-constant-time on equal-length inputs; on unequal-length
    # inputs it returns False in short-circuit but without leaking content.
    try:
        return hmac.compare_digest(expected.lower(), signature.lower())
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Sidecar I/O
# ---------------------------------------------------------------------------

def write_sidecar(signature: str, sig_path: Path) -> None:
    """Write a signature to a ``.sig`` sidecar file.

    File format v1: a single line containing the 64-char hex digest + ``\\n``.
    No JSON wrapper — keeps the format trivially verifiable with ``cat`` /
    ``shasum`` + the documented procedure.

    PR-5c.1 per Codex L1: strict hex-shape validation on write. A caller
    that produces a malformed signature should fail at write time rather
    than persist junk that verify() would later reject.

    Raises
    ------
    ValueError
        When the signature is not exactly 64 hex characters (case-
        insensitive). Empty string, wrong length, multi-line, or
        non-hex content all fail.
    """
    stripped = signature.strip() if signature else ""
    if not _HEX_SIG_RE.match(stripped):
        raise ValueError(
            f"signature must be exactly 64 hex chars; got {len(stripped)} "
            f"chars. Sidecar write refused to prevent corrupt audit artifacts."
        )
    sig_path.parent.mkdir(parents=True, exist_ok=True)
    sig_path.write_text(stripped + "\n", encoding="utf-8")


def read_sidecar(sig_path: Path) -> Optional[str]:
    """Read a signature from a ``.sig`` sidecar file.

    Returns the validated hex digest, or None if the file is missing,
    empty, unreadable, or has malformed content (wrong length, non-hex
    characters, multi-line). Callers treat None as "no signature" — do
    not confuse with "verify False".

    PR-5c.1 per Codex L1: strict hex-shape validation on read prevents
    a malformed sidecar from being passed to verify(), where it would
    silently return False and make the operator wonder whether the
    signature failed tamper-check vs. was never well-formed.
    """
    if not sig_path.is_file():
        return None
    try:
        text = sig_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    if not _HEX_SIG_RE.match(text):
        return None
    return text


__all__ = [
    "HMAC_ENV_VAR",
    "DOMAIN_TAG",
    "HmacSecretMissing",
    "get_hmac_secret_from_env",
    "sign",
    "verify",
    "write_sidecar",
    "read_sidecar",
]
