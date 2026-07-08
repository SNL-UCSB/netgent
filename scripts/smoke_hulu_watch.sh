#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-netgent:amd64}"
MODE="${MODE:-execute}" # execute or generate
PORT="${PORT:-8080}"
EXECUTABLE_CODE="${EXECUTABLE_CODE:-$PWD/out/hulu-watch_state_repository.json}"
FOLLOW_LOGS="${FOLLOW_LOGS:-1}"
FILTER_LOGS="${FILTER_LOGS:-1}"
ENV_ARGS=(-e HULU_EMAIL -e HULU_PASSWORD -e HULU_PROFILE_NAME)

if [[ -f "$PWD/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PWD/.env"
  set +a
fi

: "${HULU_EMAIL:?Set HULU_EMAIL in .env before running Hulu workflow}"
: "${HULU_PASSWORD:?Set HULU_PASSWORD in .env before running Hulu workflow}"
: "${HULU_PROFILE_NAME:?Set HULU_PROFILE_NAME in .env before running Hulu workflow}"

if [[ "$MODE" == "execute" && ! -f "$EXECUTABLE_CODE" ]]; then
  echo "Missing executable workflow: $EXECUTABLE_CODE" >&2
  echo "Run MODE=generate $0 first, or set EXECUTABLE_CODE=/path/to/workflow.json." >&2
  exit 1
fi

mkdir -p "$PWD/browser_cache/hulu-watch"
docker build --platform linux/amd64 -t "$IMAGE_NAME" .
docker run --rm --entrypoint sh \
  -v "$PWD/browser_cache/hulu-watch:/cache" \
  "$IMAGE_NAME" \
  -lc 'rm -f /cache/Default/LOCK /cache/SingletonCookie /cache/SingletonLock /cache/SingletonSocket'

case "$MODE" in
  execute)
    cid="$(docker run --platform=linux/amd64 --rm -d \
      "${ENV_ARGS[@]}" \
      -p "$PORT:8080" \
      -v "$EXECUTABLE_CODE:/executable_code.json:ro" \
      -v "$PWD/out:/out" \
      -v "$PWD/browser_cache/hulu-watch:/tmp/browser-cache" \
      "$IMAGE_NAME" \
      -e /executable_code.json \
      --user-data-dir /tmp/browser-cache \
      -o /out/hulu-watch_execution_result.json \
      -s)"
    ;;
  generate)
    cid="$(docker run --platform=linux/amd64 --rm -d \
      "${ENV_ARGS[@]}" \
      -p "$PORT:8080" \
      -v "$PWD/api_keys.json:/keys.json:ro" \
      -v "$PWD/examples/web_browsing/hulu-watch/prompts/hulu-watch_prompts.json:/prompts.json:ro" \
      -v "$PWD/out:/out" \
      -v "$PWD/browser_cache/hulu-watch:/tmp/browser-cache" \
      "$IMAGE_NAME" \
      -g /keys.json '{}' /prompts.json \
      --user-data-dir /tmp/browser-cache \
      -o /out/hulu-watch_state_repository.json \
      -s)"
    ;;
  *)
    echo "Usage: MODE=execute|generate $0" >&2
    exit 2
    ;;
esac

echo "Container: $cid"
echo "noVNC: http://localhost:$PORT"
echo "Logs: docker logs -f $cid"

if [[ "$FOLLOW_LOGS" == "1" ]]; then
  if [[ "$FILTER_LOGS" == "1" ]]; then
    docker logs -f "$cid" 2>&1 | grep --line-buffered -E "^(Mode:|Running|Using|Loaded|Starting|No states passed|CHOICE:|AVAILABLE_TRIGGER_TYPES:|TRIGGERS:|Result:|State checking took|TERMINATING:|Error:|Results saved|Task completed|Execution completed|Code generation completed|\\{'type':)"
  else
    docker logs -f "$cid"
  fi
fi
