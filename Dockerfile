# syntax=docker/dockerfile:1.7

# ── netgent image ─────────────────────────────────────────────────────────────
# Two-layer install pattern: dependencies baked once, source code swapped
# separately so code-only changes don't invalidate the deps cache.
#
# Playwright **browser binaries** are intentionally not installed. The app
# drives a remote Browserless instance via CDP, so it only needs the
# Playwright Python package (already a runtime dep).

FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# 1. Dependencies layer — cached unless lockfile or manifest changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 2. App layer — invalidates only when source changes. No second
#    `uv sync` because pyproject.toml has no [build-system] — there's
#    no installable project artifact. Source lives next to .venv and
#    is reached by path (e.g. `python scripts/run_netgent.py`).
COPY . .

# Make .venv binaries (python, pytest, ruff) directly callable.
ENV PATH="/app/.venv/bin:$PATH"

# No server entrypoint — netgent is a library + scripts. Stay alive
# for `docker compose exec`; override with `compose run --rm netgent
# python scripts/...` for one-shots.
CMD ["sleep", "infinity"]
