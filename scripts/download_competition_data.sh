#!/usr/bin/env bash
# Autonomous, idempotent competition data restoration & feature preparation for GEMSDOE84.
# DrivenData portal downloads (https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
# require interactive browser login; this script restores the SHA-256-pinned public GitHub mirrors
# listed in registry/data_manifest.json and prepares the 96-channel H84-THMS stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p "$ROOT/.cache/gems_data/external" "$ROOT/.cache/gems_data/scored" "$ROOT/.cache/gems_data/processed" "$ROOT/data/bridge"
ln -sfn "$ROOT/.cache/gems_data" "$ROOT/data/raw"

echo "[1/2] Restoring & verifying SHA-256-pinned competition and external datasets..."
python3 "$ROOT/scripts/restore_data.py" --target-dir "$ROOT/.cache/gems_data"

echo "[2/2] Preparing grid audit, 72-channel physical stack, and registry halo bitmatrix..."
python3 "$ROOT/scripts/prepare_data.py"

echo "Data restoration and preparation complete."
