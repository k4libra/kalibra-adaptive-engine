# Kalibra Adaptive Engine API

## Summary

Kalibra Adaptive Engine API, a stateless AI service built with Python and the FastAPI
framework, following Domain-Driven Design. It estimates each student's mastery per
subtopic with Bayesian Knowledge Tracing, generates multiple-choice exercises anchored
to the course material, and verifies every exercise before it can reach a student.
Each bounded context lives as an internal package with its own domain, application,
infrastructure and interfaces layers, and contexts communicate in-process through Open
Host Services. The engine persists nothing: `kalibra-api` (Spring Boot) orchestrates it
over HTTPS and stores every result.

## Features

- RESTful API with OpenAPI documentation grouped by tag (`/docs`), with examples and documented errors
- Domain-Driven Design (bounded context per package, pure-Python domain)
- Bayesian Knowledge Tracing mastery estimation
- Exercise generation with DeepSeek V4-Flash
- Rule-based verification with DeepSeek V4-Pro fallback
- Curricular extraction with Mistral OCR
- Fully asynchronous I/O with a single pooled HTTP client and retries with backoff
- Bounded concurrency towards AI providers
- `camelCase` JSON contract for the Spring Boot consumer
- RFC 9457 problem-details error responses
- Redis Streams task queue with the same contract as REST (on in Docker Compose, off in a bare run)
- import-linter boundary enforcement
- Liveness and readiness health checks
- Container image and Docker Compose stack
- Continuous Integration (GitHub Actions)

## Bounded Contexts

The application is divided into internal packages, each one a bounded context with its
own domain, application, infrastructure and interfaces layers.

### Mastery Context

The Mastery Context is responsible for estimating how well a student masters a subtopic
after each answer. It includes the following features:

- Update mastery with Bayesian Knowledge Tracing: P(L0) = 0.30, P(T) = 0.10, P(G) = 0.25, P(S) = 0.10
- Start from the base mastery when the student has no history in the subtopic
- Return the prior and posterior mastery so the consumer can show how much it changed
- Classify mastery as low (< 40 %), medium (40–70 %) or high (> 70 %)
- Override the BKT parameters per subtopic through configuration

### Verification Context

The Verification Context is responsible for guaranteeing that no non-conforming exercise
reaches a student. It includes the following features:

- Check structural correctness: statement, four distinct options and a valid answer key
- Check that the declared difficulty matches the target difficulty
- Discard any exercise that fails a rule, with a reason visible to the teacher
- Escalate rule-approved exercises to DeepSeek V4-Pro, which solves them independently and judges their difficulty

It also exposes an Open Host Service (OHS) for in-process communication with other
contexts, offering the following capabilities:

- Verify an exercise against a target difficulty, returning a `VerificationSummary` with the verdict, the result of each criterion, the rejection reason and whether the fallback provider was used

### Generation Context

The Generation Context is responsible for producing verified exercises anchored to the
curriculum and for turning uploaded material into that curricular anchor. It includes
the following features:

- Choose the exercise difficulty from the student's mastery
- Generate exercises with DeepSeek V4-Flash anchored to the subtopic material
- Discard rejected exercises and generate new ones until one is approved or the attempts run out
- Return every attempt with its verification result, so rejected exercises can be audited and the approval rate measured
- Generate several exercises concurrently within a configurable limit
- Extract documents and images with Mistral OCR and normalize the text

It relies on an anti-corruption layer (ACL) to consume the Verification Context,
translating its contract into this context's own model.

## Technology Stack

| Concern | Technology |
|---|---|
| Language | Python 3.13 |
| Framework | FastAPI 0.141 · Starlette 1.7 · Uvicorn 0.54 |
| Validation and settings | Pydantic 2.13 · pydantic-settings 2.15 |
| Outbound HTTP | HTTPX 0.28 · Tenacity 9.1 |
| Task queue | Redis 8 Streams · redis-py 8.1 |
| AI providers | DeepSeek V4-Flash · DeepSeek V4-Pro · Mistral OCR |
| Tooling | uv · Ruff · mypy (strict) · import-linter · pytest · Docker · GitHub Actions |

## Project Structure

```
src/kalibra_engine/
├── main.py            Application factory: routers, lifespan, exception mapping.
├── mastery/           Core — BKT mastery estimation.
├── verification/      Core — exercise verification (OHS for generation).
├── generation/        Core — exercise generation and curricular extraction.
└── shared/            Cross-cutting: settings, HTTP client, lifespan, error handler.

<context>/
├── dependencies.py    Composition root (FastAPI dependencies).
├── domain/            Aggregates, entities, value objects, commands, domain services.
├── application/       Command services, ACLs, OHS implementation.
├── infrastructure/    Provider adapters and configuration.
└── interfaces/        REST routers and schemas, queue task handlers, or the OHS contract.
```

## Getting Started

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

### Configuration

```bash
cp .env.example .env   # then set DEEPSEEK_API_KEY and MISTRAL_API_KEY
```

The two provider keys are the only values you have to fill in. Every other setting has
a working default, listed and explained in `.env.example` (models, timeouts, generation
attempts, concurrency, BKT parameters and the Redis queue).

The engine also boots without keys, logging a warning for each missing one:

| Capability | Without keys |
|---|---|
| Mastery estimation | Works: it needs no AI provider |
| Exercise generation and verification | `502` until `DEEPSEEK_API_KEY` is set |
| Curricular extraction | `502` until `MISTRAL_API_KEY` is set |
| `GET /health/live` | `200` |
| `GET /health/ready` | `503`, naming the missing key |

### Running the application

```bash
uv sync
uv run fastapi dev src/kalibra_engine/main.py   # development, with reload
```

Or run the container image together with Redis:

```bash
docker compose up --build                        # engine on :8000, Redis on :6379, task worker on
REDIS_ENABLED=false docker compose up --build    # same, REST only
```

A bare run serves REST only; set `REDIS_ENABLED=true` (and `REDIS_URL`) to also consume
the task queue.

### API documentation

Swagger UI is served at `http://localhost:8000/docs` (ReDoc at `/redoc`, the document
at `/openapi.json`). Operations are grouped by tag:

| Tag | Operations |
|---|---|
| `Mastery` | `POST /api/v1/mastery-estimates` |
| `Generation` | `POST /api/v1/exercise-generations` |
| `Extraction` | `POST /api/v1/curricular-extractions` |
| `Health` | `GET /health/live`, `GET /health/ready` |

Every field carries a description and an example, and every operation documents the
errors it can return. Verification has no endpoint: it runs in-process inside generation.

## Task Queue

Besides REST, the engine can consume tasks that `kalibra-api` publishes on a Redis
stream and publish each outcome on a results stream, with the same JSON contract as the
REST endpoints. The worker runs when `REDIS_ENABLED=true`, which is the default in the
Docker Compose stack and off in a bare run. The full contract and
delivery guarantees are in [`docs/redis-task-queue.md`](docs/redis-task-queue.md).

## Security

The engine has no authentication yet: it is an internal service meant to be reachable
only by `kalibra-api` inside the private network. Provider keys are read from the
environment and never logged or returned; provider failures are reported without
their details.

The container image runs as a non-root user, contains only the virtual environment (no
source tree, tests or build tools) and never includes `.env`: configuration is injected
at runtime through environment variables.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/mastery-estimates` | Estimate mastery after an answer (201) |
| `POST` | `/api/v1/exercise-generations` | Generate verified exercises (201) |
| `POST` | `/api/v1/curricular-extractions` | Extract and normalize material (201) |
| `GET` | `/health/live` | Liveness: the process is up (container health check) |
| `GET` | `/health/ready` | Readiness: HTTP client open, provider keys set, Redis reachable when enabled; `503` otherwise |

## Error Handling

`shared/interfaces/rest/EngineExceptionHandler` turns business exceptions into
`application/problem+json` responses (RFC 9457):

| Status | When |
|---|---|
| `422` | Invalid probability, or a material that is itself unusable (mark it as an ingestion error) |
| `409` | An attempt registered on an exhausted generation run |
| `502` | An AI provider is unreachable, misconfigured or answers badly; details are only logged |

For curricular extraction the split between `422` and `502` decides whether the teacher
has to replace the material, so it follows who is at fault:

| Extraction outcome | Status |
|---|---|
| Unsupported `format` | `422` |
| Mistral OCR rejects the document (`400`, `413`, `415` or `422`) | `422` |
| The extracted material has no text | `422` |
| `MISTRAL_API_KEY` missing, or rejected by Mistral (`401`, `403`) | `502` |
| Transport error or timeout | `502` |
| Mistral answers `408`, `429` or `5xx` after the engine's retries | `502` |
| Any other Mistral status, or a response the engine cannot read | `502` |

FastAPI keeps resolving its own errors: a request that does not match the schema gets
`422` with FastAPI's `application/json` validation body, not problem details. Failed queue
tasks carry the same problem details in their result.

## Testing

```bash
uv run pytest --cov=kalibra_engine   # full suite; providers are simulated, no network
uv run lint-imports                  # bounded-context boundaries
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

Every layer has a worked test example: domain rules, command services with fakes,
provider adapters with `httpx.MockTransport`, REST end-to-end tests that run the real
generation-verification loop against simulated providers, and task-queue tests against
an in-memory Redis.

CI (`.github/workflows/ci.yml`) runs every check above on each push and pull request to
`main` and `develop` (coverage must stay at or above 70 %), then builds the container
image and smoke-tests it.
