#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-netgent:amd64}"
MODE="${MODE:-execute}" # execute or generate

docker build --platform linux/amd64 -t "$IMAGE_NAME" .

case "$MODE" in
  execute)
    docker run --platform=linux/amd64 --rm -d \
      -p 8080:8080 \
      -v "$PWD/examples/video_streaming/twitch-247jynxzi/results/twitch-247jynxzi_result.json:/executable_code.json:ro" \
      -v "$PWD/out:/out" \
      "$IMAGE_NAME" \
      -e /executable_code.json \
      --user-data-dir /tmp/browser-cache \
      -o /out/twitch-247jynxzi_execution_result.json \
      -s
    ;;
  generate)
    docker run --platform=linux/amd64 --rm -d \
      -p 8080:8080 \
      -v "$PWD/api_keys.json:/keys.json:ro" \
      -v "$PWD/examples/video_streaming/twitch-247jynxzi/prompts/twitch-247jynxzi_prompts.json:/prompts.json:ro" \
      -v "$PWD/out:/out" \
      "$IMAGE_NAME" \
      -g /keys.json '{}' /prompts.json \
      --user-data-dir /tmp/browser-cache \
      -o /out/twitch-247jynxzi_state_repository.json \
      -s
    ;;
  *)
    echo "Usage: MODE=execute|generate $0" >&2
    exit 2
    ;;
esac
