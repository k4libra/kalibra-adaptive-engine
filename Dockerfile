# syntax=docker/dockerfile:1
# No BuildKit cache or bind mounts: Railway rejects cache mounts without a hard-coded service-id
# prefix, so dependency caching relies on the layer reused while pyproject.toml and uv.lock do not change.

# ---- Build: resolve the locked dependencies and install the engine into a venv ----
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_CACHE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-editable --no-dev

COPY src ./src
RUN uv sync --locked --no-editable --no-dev

# ---- Runtime: only the venv, no build tools, no source tree, non-root user ----
FROM python:3.13-slim

RUN groupadd --system engine && useradd --system --gid engine --no-create-home engine

COPY --from=builder --chown=engine:engine /app/.venv /app/.venv

# UVICORN_HOST/UVICORN_PORT are read by uvicorn itself; set UVICORN_HOST=:: on IPv6-only private networks.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000

WORKDIR /app
USER engine
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request; sys.exit(urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('UVICORN_PORT', '8000')}/health/live\", timeout=2).status != 200)"]

CMD ["uvicorn", "kalibra_engine.main:app", "--proxy-headers"]
