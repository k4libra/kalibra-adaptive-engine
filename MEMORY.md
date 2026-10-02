# MEMORY.md - Kalibra Adaptive Engine

Inter-session project memory. This file contains ~50 lines: summarize or remove content that no longer adds value.

## Current status (2026-10-02)
- Three bounded contexts (`mastery`, `generation`, `verification`) implemented and merged in `develop`.
- Branch `feature/openapi-docs-and-readiness` (not merged, not pushed): OpenAPI grouped by tags
  (`Mastery`, `Generation`, `Extraction`, `Health`) with examples and documented errors; readiness
  with only the two provider keys; extraction 422/502 fix.
- Gates green on that branch: ruff, mypy strict, import-linter, pytest (189 tests, ~99 % coverage).

## Decisions (and why)
- `ProblemDetails` (`shared/interfaces/rest/problem_details.py`) only documents errors in OpenAPI;
  `EngineExceptionHandler` still builds the bodies, so the wire output did not change. It is not in
  the validated class diagram yet: add it there.
- `problem_responses.py` documents errors under `application/problem+json` and adds the schemas to
  the generated document, because FastAPI only registers models used as `application/json`.
- Endpoints that declare their own `422` must also document FastAPI's validation body
  (`application/json`, `HTTPValidationError`): declaring `422` removes FastAPI's default one.
- Extraction: `422` only when the material is at fault (unsupported format, Mistral `400`, `413`,
  `415`, `422`, or no text). Missing key, `401`/`403`, transport errors, `408`/`429`/`5xx` and any
  other provider failure are `502`, so kalibra-api retries instead of marking an ingestion error.
- `REDIS_ENABLED` defaults to `true` only in `docker-compose.yml` (its stack has Redis); `Settings`
  keeps `False` so a bare run and the CI image smoke test need no Redis.
- The app version comes from package metadata (`engine_version()` in `main.py`), `0.0.0` fallback.
- Missing provider keys never fail boot: the lifespan logs one warning per key.

## Lessons learned and mistakes to avoid
- `.env.example` must not set `REDIS_ENABLED`: compose interpolates `.env`, so a copied `false`
  would silently turn the worker off in the compose stack.
- import-linter's logging config (run by `tests/architecture`) disables loggers created before it;
  tests that assert on engine logs must re-enable the logger (see `tests/shared/test_lifespan.py`).
- A Mistral `400` cannot be told apart from an engine misconfiguration (e.g. a wrong
  `MISTRAL_OCR_MODEL`) without parsing the provider body; today it counts as a bad material.
- `docker compose config` prints every variable of the local `.env`: do not paste its output.
- redis-py 8 defaults `socket_timeout` to 5 s; a blocking `XREADGROUP` of the same length timed out on every idle
  poll. `create_redis_client` keeps the socket timeout above `REDIS_BLOCK_MILLISECONDS`. fakeredis does not show this.

## Next steps (to operate the MVP)
- Merge the feature branch into `develop` after review; add `ProblemDetails` to the class diagram.
- `AGENTS.md` still says the worker is off unless `REDIS_ENABLED=true`; update it for compose.
- Open questions for the user: 409 is mapped but unreachable from the generation loop; a provider
  failure in one run of a multi-exercise request discards the attempts of the other runs.
