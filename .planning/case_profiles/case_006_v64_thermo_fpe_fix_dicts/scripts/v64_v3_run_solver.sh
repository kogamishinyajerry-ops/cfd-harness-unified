#!/usr/bin/env bash
# v64 v3 thermo-FPE fix solver pipeline (case_006):
#   1) potentialFoam pre-step → smooth incompressible velocity IC
#   2) rhoSimpleFoam steady (3000 iter cap) with fvOptions limitTemperature
#
# Substrate v3 changes vs B59 v2.3 attempt 3:
#   - system/fvOptions adds limitTemperature [110, 2000] K
#   - constant/thermophysicalProperties restored to sutherland (was const)
#   - system/fvSolution adds potentialFlow block + Phi solver
#
# Reverse condition: if potentialFoam or rhoSimpleFoam crashes, capture log
# verbatim and document in v3 validation report.
set -uo pipefail
CASE_ROOT="/Users/Zhuanz/Desktop/case_006_onera_m6_transonic"
CASE_DIR="$CASE_ROOT/case"
IMG="opencfd/openfoam-default:2312"
LOG_DIR="$CASE_DIR/log_v64_v3"
EVID_DIR="$CASE_ROOT/evidence/v64_v3"
mkdir -p "$LOG_DIR" "$EVID_DIR"

# Fresh start: restore 0/ from 0.orig if absent (or if previous run left a
# polluted state)
if [ ! -d "$CASE_DIR/0" ]; then
    cp -r "$CASE_DIR/0.orig" "$CASE_DIR/0"
fi

# Clean any time dirs from previous v3 runs (keep 0/, 0.orig/, 0.v24/)
for d in "$CASE_DIR"/*/; do
    base=$(basename "$d")
    case "$base" in
        0|0.orig|0.v24|0.v24_*|constant|constant.v24|system|system.v24|polyMesh|triSurface|log*|postProcessing*)
            ;;
        [0-9]*)
            rm -rf "$d"
            echo "[clean] removed previous time dir $base"
            ;;
    esac
done

echo "=== potentialFoam pre-step start $(date +%H:%M:%S) ==="
docker run --rm \
    --entrypoint /bin/bash \
    -v "$CASE_DIR":/case \
    -w /case \
    "$IMG" \
    -c "source /usr/lib/openfoam/openfoam2312/etc/bashrc 2>/dev/null || true; \
        potentialFoam -writephi -writep" \
    2>&1 | tee "$LOG_DIR/01_potentialFoam.log"
rc_pot="${PIPESTATUS[0]}"
echo "=== potentialFoam end $(date +%H:%M:%S) exit=$rc_pot ==="

if [ "$rc_pot" -ne 0 ]; then
    echo "potentialFoam FAILED · skipping rhoSimpleFoam · check log_v64_v3/01_potentialFoam.log"
    cp "$LOG_DIR/01_potentialFoam.log" "$EVID_DIR/" 2>/dev/null || true
    exit "$rc_pot"
fi

echo "=== rhoSimpleFoam start $(date +%H:%M:%S) ==="
docker run --rm \
    --entrypoint /bin/bash \
    -v "$CASE_DIR":/case \
    -w /case \
    "$IMG" \
    -c "source /usr/lib/openfoam/openfoam2312/etc/bashrc 2>/dev/null || true; \
        rhoSimpleFoam" \
    2>&1 | tee "$LOG_DIR/02_rhoSimpleFoam.log"
rc_solv="${PIPESTATUS[0]}"
echo "=== rhoSimpleFoam end $(date +%H:%M:%S) exit=$rc_solv ==="

cp "$LOG_DIR/01_potentialFoam.log" "$EVID_DIR/" 2>/dev/null || true
cp "$LOG_DIR/02_rhoSimpleFoam.log" "$EVID_DIR/" 2>/dev/null || true
exit "$rc_solv"
