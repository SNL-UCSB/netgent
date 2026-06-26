#!/usr/bin/env bash
# A sample non-browser NetGent workflow: ping a host to generate steady,
# low-rate background traffic. Runs concurrently alongside browser workflows.
set -euo pipefail

HOST="${PING_HOST:-8.8.8.8}"
COUNT="${PING_COUNT:-20}"

echo "[ping] pinging $HOST x$COUNT"
ping -c "$COUNT" "$HOST"
echo "[ping] done"
