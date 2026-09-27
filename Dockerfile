# syntax=docker/dockerfile:1

# ---- Build: resolve the locked dependencies and install the engine into a venv ----
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first: this layer is reused while pyproject.toml and uv.lock do not change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --no-dev

COPY pyproject.toml uv.lock ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev

# ---- Runtime: only the venv, no build tools, no source tree, non-root user ----
FROM python:3.13-slim

RUN groupadd --system engine && useradd --system --gid engine --no-create-home engine

COPY --from=builder --chown=engine:engine /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
USER engine
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status != 200)"]

CMD ["uvicorn", "kalibra_engine.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
