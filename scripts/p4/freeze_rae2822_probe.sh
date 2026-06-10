#!/usr/bin/env bash
# P4 V73.B · freeze the RAE 2822 Case 9 live-probe evidence bundle.
#
# V71.A/B probe conventions adapted: case inputs at BUNDLE ROOT (0/
# constant/ system/, NO polyMesh — blockMesh regenerates it) because the V73
# extractor consumes a case dir directly (V71 nested case_definition/ since
# its extractor read VTK+CSV instead). Live outputs under postProcessing/,
# trimmed logs under logs/, SHA256SUMS tamper manifest over everything
# (verify: cd <bundle> && shasum -a 256 -c SHA256SUMS).
#
# Usage: bash scripts/p4/freeze_rae2822_probe.sh <run_case_dir> <t_snap>
set -euo pipefail

RUN_DIR="${1:?run case dir}"
T_SNAP="${2:?snapshot time (surface write dir name)}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
BUNDLE="$REPO/reports/showcase_aero/_v73b_rae2822_probe"

# ---- validate EVERY input BEFORE any destructive step (Codex R0 P2:
# a failed refresh must not wipe the last good frozen bundle) ----------------
require() { [ -f "$1" ] || { echo "missing required input: $1" >&2; exit 1; }; }
require "$RUN_DIR/RUN_DONE"
require "$RUN_DIR/postProcessing/airfoilSurface/$T_SNAP/p_aerofoil.raw"
require "$RUN_DIR/postProcessing/forceCoeffs1/0/coefficient.dat"
require "$RUN_DIR/postProcessing/freestreamProbe/0/surfaceFieldValue.dat"
require "$RUN_DIR/postProcessing/yPlus1/0/yPlus.dat"
require "$RUN_DIR/log.blockMesh"
require "$RUN_DIR/log.checkMesh"
require "$RUN_DIR/log.rhoSimpleFoam"
require "$BUNDLE/REPRODUCE.md"
require "$BUNDLE/RESULT.md"

# REPRODUCE.md / RESULT.md are authored, not generated — carry them across
# the wipe (they are also required below, fail-closed)
STASH="$(mktemp -d)"
for f in REPRODUCE.md RESULT.md; do
    [ -f "$BUNDLE/$f" ] && cp "$BUNDLE/$f" "$STASH/"
done
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE"
cp "$STASH"/* "$BUNDLE/" 2>/dev/null || true
rm -rf "$STASH"
mkdir -p "$BUNDLE/logs" \
         "$BUNDLE/postProcessing/forceCoeffs1/0" \
         "$BUNDLE/postProcessing/freestreamProbe/0" \
         "$BUNDLE/postProcessing/airfoilSurface/$T_SNAP" \
         "$BUNDLE/postProcessing/yPlus1/0"

# case inputs at bundle root (regenerable: scripts/p4/generate_rae2822_case9.py)
cp -R "$RUN_DIR/0" "$RUN_DIR/constant" "$RUN_DIR/system" "$BUNDLE/"
rm -rf "$BUNDLE/constant/polyMesh"

# live outputs the extractor/gate consume
cp "$RUN_DIR/postProcessing/forceCoeffs1/0/coefficient.dat" \
   "$BUNDLE/postProcessing/forceCoeffs1/0/"
cp "$RUN_DIR/postProcessing/freestreamProbe/0/surfaceFieldValue.dat" \
   "$BUNDLE/postProcessing/freestreamProbe/0/"
cp "$RUN_DIR/postProcessing/airfoilSurface/$T_SNAP/p_aerofoil.raw" \
   "$BUNDLE/postProcessing/airfoilSurface/$T_SNAP/"
cp "$RUN_DIR/postProcessing/yPlus1/0/yPlus.dat" "$BUNDLE/postProcessing/yPlus1/0/"

# trimmed logs (full logs stay with the run dir, not the repo)
cp "$RUN_DIR/log.blockMesh" "$BUNDLE/logs/log.blockMesh"
tail -60 "$RUN_DIR/log.checkMesh" > "$BUNDLE/logs/log.checkMesh.tail"
{ head -80 "$RUN_DIR/log.rhoSimpleFoam"; echo; echo "[... trimmed ...]"; echo;
  tail -120 "$RUN_DIR/log.rhoSimpleFoam"; } > "$BUNDLE/logs/log.rhoSimpleFoam.headtail"

# manifest LAST (docs were pre-validated above and carried across the wipe)
( cd "$BUNDLE" && find . -type f ! -name SHA256SUMS | sort | xargs shasum -a 256 > SHA256SUMS )
echo "frozen: $BUNDLE"
( cd "$BUNDLE" && shasum -a 256 -c SHA256SUMS --quiet ) && echo "manifest verifies"
