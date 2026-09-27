# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this service is

Kalibra Adaptive Engine: a **stateless** FastAPI service (Python 3.13, managed with `uv`) that runs Kalibra's AI work: Bayesian Knowledge Tracing mastery estimation, multiple-choice exercise generation (DeepSeek V4-Flash), exercise verification (rules + DeepSeek V4-Pro fallback) and curricular extraction (Mistral OCR). It persists nothing.

## How it complements kalibra-api

[`kalibra-api`](https://github.com/k4libra/kalibra-api) (sibling repository) is the system of record and the only client of this engine. It owns users, courses, materials, students' answers and every persisted result; the engine only computes and returns. Keep that split when changing anything:

- **Two transports, one contract.** kalibra-api calls the REST endpoints over HTTPS, or publishes tasks on a Redis stream (`kalibra:engine:tasks`) and reads outcomes from `kalibra:engine:results`. A task's `payload` is exactly the REST request body and its `result` exactly the REST response body; failures are the same RFC 9457 problem details in both. Changing a schema changes both transports. The queue contract and delivery guarantees are in `docs/redis-task-queue.md`.
- **JSON is `camelCase`** on the wire (for the Java consumer), `snake_case` in Python. All schemas extend `shared/interfaces/rest/camel_model.py::CamelModel`.
- **Status codes carry meaning for kalibra-api:** `422` means the input or material is bad (don't retry; for extraction, mark the material as an ingestion error), `502` means an AI provider failed (retry later), `409`/`500` need attention.
- **Queue delivery is at least once**, so kalibra-api stores results idempotently by `taskId`. The Redis worker is off unless `REDIS_ENABLED=true`.
- **What the engine returns is what kalibra-api needs to persist:** mastery returns both `prior` and `posterior` (the consumer shows the change); generation returns every attempt, approved or discarded, with its rejection reason (the consumer audits them and computes approval rates). A rejected exercise must never appear as `approvedExercise`.
- The engine has no authentication; it is meant to be reachable only by kalibra-api on a private network. The gap-map cache in Redis belongs to kalibra-api; the engine never touches it.

## Commands

```bash
uv sync                                          # install (dev group included)
uv run fastapi dev src/kalibra_engine/main.py    # run with reload; docs at :8000/docs
docker compose up --build                        # engine + Redis 8; add REDIS_ENABLED=true for the worker

uv run pytest                                    # full suite (coverage gate: 70 %)
uv run pytest tests/generation/test_rest.py::test_rejected_exercise_is_discarded_and_regenerated
uv run pytest -k worker                          # by keyword
uv run ruff check . && uv run ruff format --check .
uv run mypy src                                  # strict
uv run lint-imports                              # bounded-context boundary contracts
```

CI (`.github/workflows/ci.yml`) runs all of the above, then builds the Docker image and smoke-tests it.

## Architecture

Domain-Driven Design, one package per bounded context under `src/kalibra_engine/`, each with four layers: `domain` → `infrastructure` → `application` → `interfaces` (higher layers may import lower ones, never the reverse).

- **`mastery`**: BKT with no aggregate (value objects + domain services). Default parameters are overridable per subtopic via `BKT_*` settings.
- **`verification`**: aggregate `ExerciseVerification`. It has **no REST endpoint**: it exposes an in-process Open Host Service, `interfaces/acl/verification_context_facade.py` (a `Protocol` plus neutral contract dataclasses), implemented in `application/acl/`.
- **`generation`**: aggregate `GenerationRun` (propose → verify → discard/retry until approved or `GENERATION_MAX_ATTEMPTS`), plus OCR extraction and normalization. It reaches verification only through its ACL `application/internal/outboundservices/acl/external_verification_service.py`.
- **`shared`**: cross-cutting only (settings, the single pooled `httpx.AsyncClient`, lifespan, Redis worker, exception handler, health). It must not import any bounded context.

Wiring worth knowing before editing:

- **Composition roots.** Each context's `dependencies.py` builds its services with FastAPI `Depends`; `main.py` composes the app, maps each domain exception to an HTTP status (`EngineExceptionHandler`), and builds the queue handlers by calling those same `dependencies.py` functions directly. A new use case therefore needs: a router in `interfaces/rest`, a task handler in `interfaces/messaging` (with a `task_type` equal to the REST resource name) and registration in `main.py`.
- **Provider adapters** (`infrastructure/providers/`) speak only the provider's language (their own Pydantic DTOs); the ACL in `application` translates to domain objects. DeepSeek calls go through `shared/infrastructure/json_chat_completion.py` (JSON mode, retries invalid content); all outbound calls use `shared/infrastructure/http_client.py::post_json` (Tenacity retries only on transport errors, 408, 429 and 5xx).
- **Domain is pure Python**: no FastAPI, Pydantic, httpx, tenacity or `shared` imports. Value objects and commands are `@dataclass(frozen=True, slots=True, kw_only=True)`; command-service interfaces are `typing.Protocol`.
- **Boundaries are enforced**, not conventional: `[tool.importlinter]` in `pyproject.toml` declares the layer, independence and purity contracts, and `tests/architecture` runs them. The only allowed cross-context imports are generation → verification's `interfaces.acl` (and between their `dependencies.py`).

## Conventions specific to this repo

- The validated class diagrams are the source of truth for class names, packages and relationships. Anything not modelled there (new classes, endpoints, infrastructure) must be proposed to the user and approved before implementing.
- Class names match the diagrams (including the `...Impl` and `...Exception` suffixes, hence ruff `N818` is ignored); one class per `snake_case.py` module.
- Code, identifiers and docstrings in English, Google-style docstrings (ruff `D`). Texts that reach teachers or students (rejection reasons, problem `detail`, LLM prompts) are in Spanish. Do not cite requirement documents (FR/NFR/US ids, section numbers) in docstrings or comments.
- Pytest runs with `filterwarnings = ["error"]`: a deprecation fails the suite. Don't use deprecated APIs (e.g. annotate `@asynccontextmanager` functions with `AsyncGenerator`, not `AsyncIterator`).
- Git flow: `main` ← `develop` ← one `feature/*` branch per unit of work. Commit messages follow `<type>(<scope>): <subject>` in English, lowercase, no body, no `Co-Authored-By`; group commits by purpose (`feat`, `test`, `build`, `chore`, `docs`).

## Testing patterns

- Tests never reach the network. Providers are simulated with `httpx.MockTransport` or fakes that subclass the adapter/ACL; Redis with `fakeredis`.
- `tests/conftest.py::running(app)` runs the real application lifespan and serves requests with its state. Use it instead of Starlette's `TestClient`, which is deprecated with `httpx`. The plain `client` fixture does not run the lifespan.
- Override settings in REST tests through `app.dependency_overrides[get_settings]`; the lifespan reads `get_settings()` directly, so queue end-to-end tests monkeypatch `shared.infrastructure.lifespan.get_settings` and `create_redis_client`.
- Every test has a 30 s timeout (`pytest-timeout`); worker tests that hang usually mean a loop is not yielding to the event loop.
