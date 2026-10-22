#!/usr/bin/env bash
# Restore hash-pinned public mirrors, NOT an authenticated organizer download.
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/restore_data.py --ids labels,existing_faults,sample_submission,ext_lidar_scarp_features_u8,ext_geodawn_rad_u8
