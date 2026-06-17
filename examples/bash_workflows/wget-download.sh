#!/usr/bin/env bash
# A sample non-browser NetGent workflow: download a file with wget to generate
# bulk-transfer network traffic. Runs concurrently alongside browser workflows.
#
# Output is written to the current working directory, which the orchestrator
# sets to out/<workflow-name>/ so parallel workflows never clobber each other.
set -euo pipefail

URL="${WGET_URL:-https://speed.hetzner.de/100MB.bin}"

echo "[wget] downloading: $URL"
wget --no-verbose --output-document=download.bin "$URL"
echo "[wget] done: $(ls -lh download.bin | awk '{print $5}')"
