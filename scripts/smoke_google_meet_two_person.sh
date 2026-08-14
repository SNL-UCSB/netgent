#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-netgent:amd64}"
PROFILE_DIR="$(cd "${1:?Usage: $0 /path/to/signed-in-chrome-profile}" && pwd)"

mkdir -p out
docker build --platform linux/amd64 -t "$IMAGE_NAME" .

docker run --platform=linux/amd64 --rm \
  -p 8080:8080 \
  -v "$PWD/examples/video_conference/google-meet-two-person/results/google-meet-two-person_result.json:/executable_code.json:ro" \
  -v "$PWD/out:/out" \
  -v "$PROFILE_DIR:/tmp/browser-cache" \
  "$IMAGE_NAME" \
  -e /executable_code.json \
  --user-data-dir /tmp/browser-cache \
  -o /out/google-meet-two-person_execution_result.json \
  -s
