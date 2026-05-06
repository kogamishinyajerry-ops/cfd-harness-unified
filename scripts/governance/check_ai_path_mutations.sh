#!/usr/bin/env bash
# DEC-V61-132 N1.2 · AI dispatch path mutation grep lint (warning-only).
#
# String-matches for known mutation call patterns in AI dispatch modules.
# Match found → prints WARNING and exits 0. Behavioral test in
# tests/test_ai_advisor_contract.py is the merge gate; this hook is the
# fast feedback layer per V132 §3.3.
#
# Why warning-only: false-positives (deprecation comments, docstrings
# referencing the symbol) would block legitimate commits. The
# behavioral sentinel test catches actual call-time violations; the
# grep hook is an early-warning advisory.
#
# Invoked by pre-commit on staged files matching the path filter
# defined in .pre-commit-config.yaml. Argument list = file paths.

set -uo pipefail

# Patterns are a) HTTP client mutation verbs, b) frontend mutation
# helper names, c) backend mutation function call sites.
PATTERNS=(
  'requests\.post'
  'requests\.put'
  'requests\.delete'
  'requests\.patch'
  'client\.post'
  'client\.put'
  'client\.delete'
  'client\.patch'
  'httpx\.post'
  'httpx\.put'
  'httpx\.delete'
  'httpx\.patch'
  '\.meshImported\('
  '\.setupBC\('
  'mesh_imported_case\('
  'setup_ldc_bc\('
  'setup_channel_bc\('
)

found=0
for file in "$@"; do
  if [ ! -f "$file" ]; then
    continue
  fi
  for pat in "${PATTERNS[@]}"; do
    if grep -nE "$pat" "$file" >/dev/null 2>&1; then
      if [ "$found" -eq 0 ]; then
        echo "[ai-path-mutation-grep] WARNING: V132 advisory layer (warning-only — behavioral test is the gate)"
        found=1
      fi
      echo "  $file: matched pattern '$pat'"
      grep -nE "$pat" "$file" 2>/dev/null | sed 's/^/    /'
    fi
  done
done

if [ "$found" -ne 0 ]; then
  echo "[ai-path-mutation-grep] If these are legitimate (e.g., deprecation"
  echo "  comments / test fixtures), no action needed — the behavioral"
  echo "  contract test (tests/test_ai_advisor_contract.py) is the gate."
fi

# Always exit 0 — advisory only.
exit 0
