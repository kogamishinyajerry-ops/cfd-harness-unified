# Audit-Package Canonical JSON Spec (v1)

> Closes **L2** from DEC-V61-014 (Codex PR-5c review, 2026-04-21).
> Implemented by [`src/audit_package/serialize.py:_canonical_json`](../../src/audit_package/serialize.py).

This document pins the exact byte-level contract the signer relies on, so
a bash / Go / Rust / anything verifier can reproduce identical input
bytes to HMAC-SHA256 over and compare against a shipped `bundle.sig`.

If you are only consuming the bundle for human review, you do not need
this doc. If you are building an **external verifier**, every clause
below is load-bearing.

---

## 1 · Encoder flags

The Python reference encoder is exactly this one call:

```python
json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
```

followed by **appending a single `\n`** and encoding the result as UTF-8:

```python
canonical_bytes = (text + "\n").encode("utf-8")
```

External verifiers must reproduce the same byte stream. Any other
encoder is acceptable **iff** it produces the identical byte sequence
for every input. The contract is byte-exact; equivalence at the AST
level is not enough.

| Flag | Value | Why |
|---|---|---|
| `sort_keys` | `True` | Stable order across Python builds, YAML-anchor order, dict-insertion order variation. |
| `ensure_ascii` | `False` | Non-ASCII identifiers in the decision trail (Chinese narrative comments, scientific notation Greek letters) must round-trip byte-for-byte; `\uXXXX` escapes break that. |
| `indent` | `2` | Line-oriented diff + page-through. Not 4, not tabs. |
| **Trailing newline** | `1` byte `0x0A` | POSIX line-oriented convention; missing-newline is the #1 cross-tool footgun. |
| **Encoding** | UTF-8, no BOM | UTF-8 is the JSON default; a BOM would shift all byte offsets. |

No separators override is used — Python's default
`(", ", ": ")` applies (not `(',', ':')`).

## 2 · Reference test vectors

Every vector below is a dict input and the exact byte output. If your
encoder disagrees with any of them, it is not spec-conforming.

### Vector A — empty dict

Input:

```python
{}
```

Output bytes (hex): `7B 7D 0A` (3 bytes)
Output text: `{}\n`

### Vector B — single scalar

Input:

```python
{"a": 1}
```

Output text:

```
{
  "a": 1
}
```

(trailing newline after the closing brace)

### Vector C — non-ASCII identifier

Input:

```python
{"summary": "测试"}
```

Output text:

```
{
  "summary": "测试"
}
```

— the CJK characters appear verbatim; NOT as `\u6d4b\u8bd5`.

### Vector D — mixed keys (sort order)

Input:

```python
{"b": 2, "a": 1, "c": [3, 2, 1]}
```

Output text:

```
{
  "a": 1,
  "b": 2,
  "c": [
    3,
    2,
    1
  ]
}
```

Keys sort; **list elements do NOT sort**. List preservation is
semantic — decision trails, input-file ordering, zip-entry ordering
all matter.

### Vector E — nested dict sort

Input:

```python
{"outer": {"zeta": 1, "alpha": 2}}
```

Output text:

```
{
  "outer": {
    "alpha": 2,
    "zeta": 1
  }
}
```

Sort recurses into every nested dict.

### Vector F — numeric types

Floats round-trip through Python's `repr`. Integers are bare. Do not
coerce ints to floats or vice versa — that changes the byte output.

```python
{"i": 1, "f": 1.5, "e": 1e-7}
```

Output text:

```
{
  "e": 1e-07,
  "f": 1.5,
  "i": 1
}
```

Note the Python-specific exponent form `1e-07` (two-digit exponent).
External encoders must match. If your encoder emits `1.0e-7` or
`1E-07` that is **non-conforming**.

### Vector G — booleans, null

```python
{"ok": True, "err": None, "done": False}
```

Output text:

```
{
  "done": false,
  "err": null,
  "ok": true
}
```

## 3 · What goes through the canonical encoder

Per [`src/audit_package/serialize.py`](../../src/audit_package/serialize.py):

| Artifact | Path inside `bundle.zip` | Encoding |
|---|---|---|
| Full manifest | `manifest.json` | canonical JSON, once |
| Whitelist case entry | `case/whitelist_entry.json` | canonical JSON |
| Gold standard | `case/gold_standard.json` | canonical JSON |

Other entries (solver logs, decision pointer stubs, verbatim input
files) are NOT re-encoded — they are copied byte-for-byte from disk
into the zip. Only dict-shaped artifacts get the canonical pass.

## 4 · Signature input framing

Defined in [`src/audit_package/sign.py`](../../src/audit_package/sign.py).

The HMAC input is:

```
DOMAIN_TAG || sha256(canonical_manifest_bytes) || sha256(zip_bytes)
```

where:

- `DOMAIN_TAG = b"cfd-harness-audit-v1|"` (22 bytes, literal UTF-8)
- `sha256(...)` is 32 bytes raw (NOT the 64-char hex text)
- `||` is byte concatenation, no separator

Total input to the HMAC function is exactly `22 + 32 + 32 = 86` bytes.

`DOMAIN_TAG` provides domain separation so the same HMAC key reused
in an unrelated context cannot produce colliding signatures.

## 5 · Signature output format

`bundle.sig` is exactly:

```
<64-char-lowercase-hex>\n
```

— 65 bytes total: 64 bytes of lowercase hex digest + one `0x0A`.

Verifiers **must** validate:

- regex `^[0-9a-f]{64}$` against the stripped line
- no other content in the file
- UTF-8 decodable

The Python writer enforces all three via `src/audit_package/sign.py:write_sidecar`.

## 6 · Byte-reproducibility end-to-end

Given the same `case_id`, `run_id`, `run_output_dir`, and `build_fingerprint`
(deterministic hash fragment per DEC-V61-019 + DEC-V61-023), **every**
byte in the output bundle should be identical across runs and hosts:

1. `manifest.json` bytes — via canonical-JSON spec (this doc).
2. `bundle.zip` bytes — via [`_fixed_zipinfo`](../../src/audit_package/serialize.py)
   (epoch mtime, fixed perms, UNIX create_system, ZIP_DEFLATED level 6).
3. `bundle.sig` bytes — via the framing in §4.

A reproducibility regression test lives at
`tests/test_audit_package/test_manifest.py::test_canonical_json_is_byte_stable_across_two_invocations`
(or equivalent) and runs in CI.

## 7 · Verifier implementation checklist

Before shipping an external verifier:

- [ ] Produce Vectors A–G byte-for-byte from §2.
- [ ] Recompute the manifest SHA-256 from your encoder's output and
      match it against the manifest hash embedded in the downloaded
      bundle (if exposed — currently it is not a separate field; the
      signature verification covers it).
- [ ] Recompute `sha256(zip_bytes)` directly from the on-disk zip.
- [ ] Construct the 86-byte HMAC input per §4.
- [ ] HMAC-SHA256 it with the shared secret key (raw bytes, not
      base64; see `CFD_HARNESS_HMAC_SECRET` env-var prefix contract
      in `src/audit_package/sign.py`).
- [ ] Compare constant-time against `bundle.sig` (lowercase hex).
- [ ] Reject if any step diverges — do not continue to the next.

## 8 · Non-goals / out of scope

- **Cross-version compatibility**: this is v1. Any future framing
  change bumps `DOMAIN_TAG` (e.g., `cfd-harness-audit-v2|`); verifiers
  must refuse mismatched tags, not fall back.
- **Key rotation / multi-signer**: see M2 follow-up in DEC-V61-014.
  v1 sidecar has no `kid` / `alg` / `domain` metadata; a v2 JSON
  sidecar is planned when retention policy requires it.
- **Timestamp certification**: `build_fingerprint` is deterministic,
  NOT a wall-clock attestation. If you need "when was this signed",
  use an external timestamping authority — do not read
  `build_fingerprint`.

## 9 · References

| Source | Link |
|---|---|
| Signer implementation | [`src/audit_package/sign.py`](../../src/audit_package/sign.py) |
| Canonical encoder | [`src/audit_package/serialize.py`](../../src/audit_package/serialize.py) |
| Manifest builder | [`src/audit_package/manifest.py`](../../src/audit_package/manifest.py) |
| DEC-V61-014 (HMAC · L2 origin) | `.planning/decisions/2026-04-21_phase5_5c_hmac_sign.md` |
| DEC-V61-019 / DEC-V61-023 | `build_fingerprint` deterministic-hash contract |
| Byte-repro zip layout | [`_fixed_zipinfo` in serialize.py](../../src/audit_package/serialize.py) |
