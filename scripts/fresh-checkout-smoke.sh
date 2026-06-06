#!/usr/bin/env bash
# Smoke test for PipeTune Linux in a clean temporary workspace.
# Copies only tracked files via git archive so the test reflects a real fresh checkout.
# Does not require root. Does not install LV2 globally. Does not modify audio config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMP_DIR="$(mktemp -d)"
SMOKE_FAILED=0

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

echo "PipeTune Linux Fresh Checkout Smoke Test"
echo "Temp workspace: $TEMP_DIR"
echo ""

SMOKE_DIR="$TEMP_DIR/pipetune-fresh"
mkdir -p "$SMOKE_DIR"
git -C "$REPO_ROOT" archive HEAD | tar -x -C "$SMOKE_DIR"

VENV_DIR="$TEMP_DIR/venv"
echo "Creating fresh virtual environment..."
python -m venv "$VENV_DIR"

echo "Installing pipetune in fresh venv..."
"$VENV_DIR/bin/pip" install --quiet -e "$SMOKE_DIR"

echo ""
echo "Running smoke checks..."
echo ""

PIPETUNE="$VENV_DIR/bin/pipetune"

run_check() {
    local label="$1"
    shift
    if "$PIPETUNE" "$@" > /dev/null 2>&1; then
        echo "- pass: $label"
    else
        echo "- fail: $label"
        SMOKE_FAILED=1
    fi
}

run_check "pipetune version" version
run_check "pipetune package inspect" package inspect
run_check "pipetune package smoke-test" package smoke-test
run_check "pipetune plugin validate --metadata" plugin validate --metadata
run_check "pipetune plugin validate --rt-safety" plugin validate --rt-safety

echo ""
if [ "$SMOKE_FAILED" -eq 0 ]; then
    echo "Final verdict: pass"
    echo "No global LV2 installation was performed."
    echo "No audio routing was changed."
    echo "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified."
else
    echo "Final verdict: fail"
    exit 1
fi
