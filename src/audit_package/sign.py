"""HMAC-SHA256 signing + verification for audit-package bundles
(Phase 5 · PR-5c · DEC-V61-014).

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
``CFD_HARNESS_HMAC_SECRET``. The value may be either:

- **base64-encoded** — preferred for high-entropy binary keys. The helper
  auto-decodes.
- **plain text** — acceptable for ad-hoc / dev keys. Encoded as UTF-8.

If neither works (empty value), :class:`HmacSecretMissing` is raised with
an install/rotation hint. **A secret is never written to stdout, logs, or
manifests.**

Rotation procedure (documented for ops):

1. Generate new random key: ``openssl rand -base64 32``
2. Set new env var for the signer service (e.g., UI backend).
3. Previously-signed bundles remain verifiable by whoever holds the **old**
   key — sidecars don't bind to a specific key ID in v1. If per-key rotation
   tracking is required, upgrade to a key-id sidecar field in a future DEC.
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
from pathlib import Path
from typing import Any, Dict, Optional

from .serialize import _canonical_json

HMAC_ENV_VAR = "CFD_HARNESS_HMAC_SECRET"
DOMAIN_TAG = b"cfd-harness-audit-v1|"
_HASH_ALGO = hashlib.sha256


class HmacSecretMissing(RuntimeError):
    """The ``CFD_HARNESS_HMAC_SECRET`` environment variable is unset/empty.

    Carries an actionable rotation-procedure hint so the caller (UI,
    CI, operator) can fix it without hunting through docs.
    """


# ---------------------------------------------------------------------------
# Key loader
# ---------------------------------------------------------------------------

def get_hmac_secret_from_env(env_var: str = HMAC_ENV_VAR) -> bytes:
    """Read the HMAC secret from the environment.

    Tries base64-decode first (standard for high-entropy binary keys);
    falls back to UTF-8 plain text if base64 decode fails.

    Raises
    ------
    HmacSecretMissing
        When the env var is unset or empty. The error message includes an
        actionable rotation hint.
    """
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        raise HmacSecretMissing(
            f"{env_var} is not set. Generate a fresh key with "
            "`openssl rand -base64 32` and export it as an environment "
            "variable before signing. See src/audit_package/sign.py module "
            "docstring for the rotation procedure."
        )
    # Try base64 first. Accept only strings whose length % 4 is 0 and only
    # contain base64-alphabet chars — prevents accidentally stripping plain
    # secrets to nonsense.
    try:
        if len(raw) % 4 == 0 and all(
            c.isalnum() or c in "+/=" for c in raw
        ):
            decoded = base64.b64decode(raw, validate=True)
            if decoded:
                return decoded
    except (binascii.Error, ValueError):
        pass
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

    File format v1: a single line containing the hex digest + `\\n`. No
    JSON wrapper — keeps the format trivially verifiable with ``cat`` /
    ``shasum`` + the documented procedure.
    """
    sig_path.parent.mkdir(parents=True, exist_ok=True)
    sig_path.write_text(signature.strip() + "\n", encoding="utf-8")


def read_sidecar(sig_path: Path) -> Optional[str]:
    """Read a signature from a ``.sig`` sidecar file.

    Returns the stripped hex digest, or None if the file is missing /
    empty / unreadable. Callers treat None as "no signature" — do not
    confuse with "verify False".
    """
    if not sig_path.is_file():
        return None
    try:
        text = sig_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


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
