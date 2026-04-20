"""Manifest → byte-reproducible zip + human-readable HTML/PDF (Phase 5 · PR-5b).

Given a manifest dict from :func:`src.audit_package.manifest.build_manifest`,
this module serializes it two ways:

- **zip**: byte-identical output for identical input. Epoch-zero mtimes,
  canonical path ordering, no system metadata, deterministic compression.
  This is the machine-verifiable evidence bundle that PR-5c HMAC-signs.

- **HTML**: semantic human-readable render of the manifest. Rendered
  inline from a string template (no Jinja, no external CDN) so the output
  is deterministic and reviewable without network access.

- **PDF**: optional; wraps the HTML output via weasyprint. Requires native
  libs (``pango``, ``cairo``, ``libgobject``) which on macOS are installed
  via ``brew install weasyprint``. When unavailable, :func:`serialize_pdf`
  raises :class:`PdfBackendUnavailable` with actionable install instructions
  rather than silently falling back — the auditor should know when PDF
  generation is skipped.

Determinism
-----------
Zip byte-equality across invocations is a hard guarantee — the PR-5c HMAC
signature covers the zip bytes, so any reordering or metadata drift would
invalidate signatures between identical runs. Enforced via:

- ``ZipInfo.date_time = (1980, 1, 1, 0, 0, 0)`` (smallest zip epoch).
- ``ZipInfo.external_attr = 0o644 << 16`` for files, ``0o755 << 16`` for
  directories. No setuid/setgid/sticky.
- Entries added in sorted path order.
- ``compress_type = ZIP_DEFLATED`` with compresslevel 6 (zlib default).
- No zip comment, no extra fields.

HTML is rendered by f-string concatenation in sorted-key order at every
dict level, so equivalent manifests produce equivalent HTML.

Non-goals
---------
- HMAC signing → PR-5c / DEC-V61-014.
- Solver invocation → out of scope entirely (caller provides manifest).
- JSON schema validation → not needed internally; would only matter if an
  external consumer parsed the dict.
"""

from __future__ import annotations

import html as _html
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Zip determinism constants
# ---------------------------------------------------------------------------

_ZIP_EPOCH: Tuple[int, int, int, int, int, int] = (1980, 1, 1, 0, 0, 0)
_FILE_PERM = 0o644 << 16
_DIR_PERM = 0o755 << 16
_COMPRESS_LEVEL = 6  # zlib default


# ---------------------------------------------------------------------------
# Canonical JSON (shared by zip + signing in PR-5c)
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> bytes:
    """JSON encode with sorted keys, UTF-8, \\n terminator.

    The trailing newline is canonical — a manifest is a line-oriented
    record, easier to diff + paginate. ``ensure_ascii=False`` preserves
    non-ASCII identifiers in the decision trail.
    """
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
    return (text + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Deterministic zip
# ---------------------------------------------------------------------------

def _fixed_zipinfo(name: str, *, is_dir: bool = False) -> zipfile.ZipInfo:
    """Build a zero-metadata ZipInfo with epoch mtime + fixed permissions."""
    info = zipfile.ZipInfo(filename=name, date_time=_ZIP_EPOCH)
    info.external_attr = _DIR_PERM if is_dir else _FILE_PERM
    info.create_system = 3  # UNIX — prevents OS-dependent drift
    if is_dir:
        info.external_attr |= 0x10  # MS-DOS directory flag
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _zip_entries_from_manifest(manifest: Dict[str, Any]) -> Dict[str, bytes]:
    """Lay out the zip entries as ``{path: bytes}`` before writing.

    Layout:

    - ``manifest.json`` — canonical JSON dump of the full manifest dict.
    - ``case/whitelist_entry.json`` — whitelist case dict (canonical JSON).
    - ``case/gold_standard.json`` — gold standard dict (canonical JSON).
    - ``run/inputs/<path>`` — each verbatim solver input file.
    - ``run/outputs/solver_log_tail.txt`` — solver log tail (if present).
    - ``decisions/DEC-*.txt`` — one-line pointer per decision-trail entry.

    All paths are POSIX-style; no leading slash; no Windows separators.
    """
    entries: Dict[str, bytes] = {}

    entries["manifest.json"] = _canonical_json(manifest)

    case = manifest.get("case") or {}
    if case.get("whitelist_entry"):
        entries["case/whitelist_entry.json"] = _canonical_json(case["whitelist_entry"])
    if case.get("gold_standard"):
        entries["case/gold_standard.json"] = _canonical_json(case["gold_standard"])

    run = manifest.get("run") or {}
    run_inputs = run.get("inputs") or {}
    for rel_path, content in sorted(run_inputs.items()):
        if rel_path == "0/" and isinstance(content, dict):
            for field_name, field_body in sorted(content.items()):
                if isinstance(field_body, str):
                    entries[f"run/inputs/0/{field_name}"] = field_body.encode("utf-8")
        elif isinstance(content, str):
            entries[f"run/inputs/{rel_path}"] = content.encode("utf-8")

    run_outputs = run.get("outputs") or {}
    log_tail = run_outputs.get("solver_log_tail")
    if isinstance(log_tail, str):
        entries["run/outputs/solver_log_tail.txt"] = log_tail.encode("utf-8")

    decisions = manifest.get("decision_trail") or []
    for decision in decisions:
        did = decision.get("decision_id") or "UNKNOWN"
        title = decision.get("title") or ""
        path = decision.get("relative_path") or ""
        body = f"decision_id: {did}\ntitle: {title}\nrelative_path: {path}\n"
        entries[f"decisions/{did}.txt"] = body.encode("utf-8")

    return entries


def serialize_zip_bytes(manifest: Dict[str, Any]) -> bytes:
    """Build the audit-package zip as bytes, byte-identical across calls.

    The function is pure: same input → same bytes. This is the property
    PR-5c's HMAC signature depends on.
    """
    entries = _zip_entries_from_manifest(manifest)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", allowZip64=False) as zf:
        for path in sorted(entries.keys()):
            info = _fixed_zipinfo(path, is_dir=False)
            zf.writestr(info, entries[path], compresslevel=_COMPRESS_LEVEL)
    return buf.getvalue()


def serialize_zip(manifest: Dict[str, Any], output_path: Path) -> None:
    """Write the byte-reproducible zip to ``output_path`` (overwrites)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(serialize_zip_bytes(manifest))


# ---------------------------------------------------------------------------
# HTML render
# ---------------------------------------------------------------------------

_CSS = """\
body { font-family: -apple-system, system-ui, sans-serif; max-width: 960px;
       margin: 2em auto; padding: 0 1em; color: #222; line-height: 1.45; }
h1 { border-bottom: 2px solid #333; padding-bottom: 0.3em; }
h2 { margin-top: 1.8em; color: #444; }
h3 { margin-top: 1.2em; color: #555; font-size: 1.05em; }
table { border-collapse: collapse; width: 100%; margin: 0.5em 0 1em; }
th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; vertical-align: top; font-size: 0.92em; }
th { background: #f0f0f0; font-weight: 600; }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
           background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }
pre { padding: 10px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }
.verdict-pass { color: #0a7d2d; font-weight: 600; }
.verdict-fail { color: #b42318; font-weight: 600; }
.verdict-hazard { color: #b07007; font-weight: 600; }
.meta { color: #666; font-size: 0.85em; }
ul.decisions li { margin: 0.3em 0; }
"""


def _esc(value: Any) -> str:
    return _html.escape(str(value), quote=True)


def _render_kv_table(data: Dict[str, Any]) -> str:
    rows = []
    for k in sorted(data.keys()):
        rows.append(f"<tr><th>{_esc(k)}</th><td>{_esc(data[k])}</td></tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def _render_verdict(verdict: Optional[str]) -> str:
    if verdict == "PASS":
        return '<span class="verdict-pass">PASS</span>'
    if verdict == "FAIL":
        return '<span class="verdict-fail">FAIL</span>'
    if verdict == "HAZARD":
        return '<span class="verdict-hazard">HAZARD</span>'
    return _esc(verdict or "UNKNOWN")


def render_html(manifest: Dict[str, Any]) -> str:
    """Render a deterministic semantic HTML document from the manifest.

    Output order is fixed (header → git → case → run → measurement →
    decisions) so two identical manifests produce identical HTML bytes.
    """
    manifest_id = _esc(manifest.get("manifest_id") or "UNKNOWN")
    generated_at = _esc(manifest.get("generated_at") or "")
    schema_version = _esc(manifest.get("schema_version") or "")

    git = manifest.get("git") or {}
    git_rows = "\n".join(
        f"<tr><th>{_esc(k)}</th><td><code>{_esc(git.get(k) or '—')}</code></td></tr>"
        for k in sorted(git.keys())
    )

    case = manifest.get("case") or {}
    case_id = _esc(case.get("id") or "UNKNOWN")
    legacy_ids = case.get("legacy_ids") or []
    legacy_html = (
        "<p><strong>Legacy ids:</strong> " + ", ".join(f"<code>{_esc(x)}</code>" for x in legacy_ids) + "</p>"
        if legacy_ids else ""
    )
    whitelist = case.get("whitelist_entry") or {}
    gold = case.get("gold_standard") or {}
    whitelist_json = _esc(json.dumps(whitelist, sort_keys=True, ensure_ascii=False, indent=2))
    gold_json = _esc(json.dumps(gold, sort_keys=True, ensure_ascii=False, indent=2))

    run = manifest.get("run") or {}
    run_status = _esc(run.get("status") or "UNKNOWN")
    run_id = _esc(run.get("run_id") or "—")
    solver = _esc(run.get("solver") or "—")
    run_kv = {"run_id": run_id, "status": run_status, "solver": solver}
    outputs = run.get("outputs") or {}
    log_tail = outputs.get("solver_log_tail") or ""

    measurement = manifest.get("measurement") or {}
    verdict = _render_verdict(measurement.get("comparator_verdict"))
    key_quantities = measurement.get("key_quantities") or {}
    kq_html = _render_kv_table(key_quantities) if key_quantities else "<p class=\"meta\">(no measurement recorded)</p>"
    concerns = measurement.get("audit_concerns") or []
    concerns_html = (
        "<ul>" + "".join(
            f"<li><code>{_esc(c.get('code', 'UNKNOWN'))}</code>: {_esc(c.get('severity', ''))} — {_esc(c.get('note', ''))}</li>"
            for c in concerns
        ) + "</ul>"
        if concerns else "<p class=\"meta\">(no audit concerns flagged)</p>"
    )

    decisions = manifest.get("decision_trail") or []
    decisions_html = (
        '<ul class="decisions">' + "".join(
            f"<li><strong>{_esc(d.get('decision_id', '?'))}</strong> — {_esc(d.get('title', ''))} <span class='meta'>(<code>{_esc(d.get('relative_path', ''))}</code>)</span></li>"
            for d in decisions
        ) + "</ul>"
        if decisions else "<p class=\"meta\">(no decision trail found)</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Audit Package — {manifest_id}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Audit Package Manifest</h1>
<p class="meta"><strong>Manifest ID:</strong> <code>{manifest_id}</code><br>
<strong>Schema:</strong> v{schema_version} &middot; <strong>Generated:</strong> {generated_at}</p>

<h2>Git provenance</h2>
<table>
{git_rows}
</table>

<h2>Case</h2>
<p><strong>Canonical id:</strong> <code>{case_id}</code></p>
{legacy_html}

<h3>Whitelist entry</h3>
<pre>{whitelist_json}</pre>

<h3>Gold standard</h3>
<pre>{gold_json}</pre>

<h2>Run</h2>
{_render_kv_table(run_kv)}

<h3>Solver log tail</h3>
<pre>{_esc(log_tail) or '(no log captured)'}</pre>

<h2>Measurement</h2>
<p><strong>Verdict:</strong> {verdict}</p>

<h3>Key quantities</h3>
{kq_html}

<h3>Audit concerns</h3>
{concerns_html}

<h2>Decision trail</h2>
{decisions_html}

</body>
</html>
"""


# ---------------------------------------------------------------------------
# PDF (weasyprint — guarded)
# ---------------------------------------------------------------------------

class PdfBackendUnavailable(RuntimeError):
    """Raised when weasyprint or its native libs cannot be imported.

    Carries an actionable install-instruction string so the UI / CLI /
    test harness can surface the fix to the user without guessing.
    """


def _import_weasyprint_module():
    """Try to import weasyprint; return (module, None) or (None, error_str)."""
    try:
        import weasyprint as _wp
        return _wp, None
    except ImportError as e:
        return None, f"weasyprint Python package not installed: {e}. Run `pip install weasyprint`."
    except OSError as e:
        return None, (
            f"weasyprint native libs unavailable: {e}. "
            "On macOS: `brew install weasyprint` (installs pango + cairo + glib). "
            "On Debian/Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`. "
            "See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation"
        )
    except Exception as e:  # noqa: BLE001 — some weasyprint configs raise other classes
        return None, f"weasyprint initialization failed: {type(e).__name__}: {e}"


def is_pdf_backend_available() -> bool:
    """Public helper — UI can surface this state without catching exceptions."""
    module, _ = _import_weasyprint_module()
    return module is not None


def serialize_pdf(manifest: Dict[str, Any], output_path: Path) -> None:
    """Render the manifest HTML to PDF via weasyprint.

    Raises
    ------
    PdfBackendUnavailable
        When weasyprint or its native libs cannot be loaded. The error
        message includes actionable installation instructions for the
        user's platform.
    """
    wp, error = _import_weasyprint_module()
    if wp is None:
        raise PdfBackendUnavailable(error or "weasyprint unavailable")
    html = render_html(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wp.HTML(string=html).write_pdf(str(output_path))


__all__ = [
    "PdfBackendUnavailable",
    "is_pdf_backend_available",
    "render_html",
    "serialize_pdf",
    "serialize_zip",
    "serialize_zip_bytes",
]
