# UX Principles

These are the rules the product-ui-director enforces. They override aesthetic
preferences and "but it would be cooler if…"

## 1. One-minute test

A reasonable engineer should be able to look at `docs/status/COCKPIT.md` (or
the HTML version) and state the project's current state in under 60 seconds.

If they can't, the cockpit is broken.

## 2. Three Phase-0 screens, no more

- **Case Contract** — view + validate `case_manifest.yaml`
- **Run Timeline** — residuals, log tail, gate status
- **Trust Report** — gates, artifacts, limitations

Anything else is a Phase 3+ concern. Do not draw mockups of "the workbench"
in v0.

## 3. Mocked status is never hidden

If `solver_execution == "mocked"`, every screen that shows status must show
"MOCKED." Not gray, not subtle — visible.

## 4. PASS is earned, not asserted

The cockpit may show PASS for a case only when the underlying trust_report's
`overall_status == PASS` and `solver_execution == "real"`. Otherwise PASS is
hidden in favor of WARN / MOCKED / FAIL.

## 5. Every status maps to an artifact

Each badge / count / icon must be hoverable (in HTML) or footnoted (in MD) to
the exact file the claim is derived from. No badge without a backing file.

## 6. AI advisor output is bracketed

The advisor's natural-language output appears in a clearly bordered block
labeled "AI advisor — advisory only." It never appears in the same visual
register as the trust gates.

## 7. No dark patterns

- no "submit" button that silently runs the solver
- no "approve" button that modifies the case
- no "AI suggests fix" button that edits the manifest without diff review
- no animations that disguise long-running operations as instant

## 8. Read before write

Phase 3 screens are read-only. The trust loop is invoked from the CLI.
Writing case data via the UI is a Phase 4+ concern, not Phase 3.
