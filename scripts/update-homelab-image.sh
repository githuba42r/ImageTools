#!/usr/bin/env bash
#
# Run the ImageTools update on the home lab over SSH.
#
#   scripts/update-homelab-image.sh
#   scripts/update-homelab-image.sh --check
#
# Override the host with HOMELAB_HOST (default: philg@home).
set -euo pipefail

HOST="${HOMELAB_HOST:-philg@home}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ssh "$HOST" 'bash -s' -- "$@" < "$SCRIPT_DIR/homelab/update-imagetools.sh"
