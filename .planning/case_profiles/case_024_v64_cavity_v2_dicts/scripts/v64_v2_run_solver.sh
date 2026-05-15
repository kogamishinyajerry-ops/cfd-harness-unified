#!/usr/bin/env bash
# case_024 v2 · Lid-Driven Cavity Re=1000 · stretched 257x257 grid
# Q1 LLM-offline runnable: env -i HOME PATH .venv/bin/python ./scripts/v64_v2_run_solver.sh
#
# Idempotent: blockMesh / checkMesh / simpleFoam / postProcess invocations
# all run inside opencfd/openfoam-default:2312 with --rm (no container state).

set -euo pipefail

SBOX="${SBOX:-$HOME/Desktop/case_024_lid_driven_cavity/case_re1000_v2_stretched}"
IMAGE="opencfd/openfoam-default:2312"

if [[ ! -d "$SBOX" ]]; then
    echo "ERROR: sandbox dir $SBOX does not exist" >&2
    exit 1
fi

echo "==> blockMesh (stretched 257x257 vertex / 256x256 cells / double-sided 5:1)"
docker run --rm -v "$SBOX":/case "$IMAGE" \
    bash -c 'cd /case && blockMesh 2>&1 | tee log.blockMesh'

echo "==> checkMesh"
docker run --rm -v "$SBOX":/case "$IMAGE" \
    bash -c 'cd /case && checkMesh 2>&1 | tee log.checkMesh'

echo "==> simpleFoam (residualControl 1e-7 strict)"
docker run --rm -v "$SBOX":/case "$IMAGE" \
    bash -c 'cd /case && simpleFoam 2>&1 | tee log.simpleFoam'

echo "==> postProcess sampleDict (centerlines)"
docker run --rm -v "$SBOX":/case "$IMAGE" \
    bash -c 'cd /case && postProcess -func sampleDict -latestTime 2>&1 | tee log.postProcess'

echo "==> extract_centerlines_v2.py (Ghia 1982 Re=1000 delta vs OF)"
DICTS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$DICTS_DIR/extract_centerlines_v2.py" \
    --case-dir "$SBOX" \
    --out "$DICTS_DIR/results"

echo "==> DONE"
