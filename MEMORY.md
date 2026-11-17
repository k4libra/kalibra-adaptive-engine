# MEMORY.md - Kalibra Adaptive Engine

Inter-session project memory. This file contains ~50 lines: summarize or remove content that no longer adds value.

## Current status (2026-11-16)
- Internal `GET /api/v1/capabilities` implemented with camelCase booleans, OpenAPI and four key combinations/no secret leaks or provider calls tested. Gates pass: ruff, format, mypy strict, 4 import contracts, pytest (207 passed, 99.08% coverage).
- Optional REST `targetDifficulty` implemented through the generation command and aggregate; omitted/null preserves mastery bands. All gates pass: ruff, format, mypy strict, 4 import contracts, pytest (203 passed, 99.07% coverage).
- Structured exercise feedback implemented: provider DTO/prompt → pure `ExplanationStep` dataclass → ACL → REST `explanationSteps`/`keyIdea`, including every attempt. Gates: ruff, format (170 files), mypy (141 files), import-linter (4 contracts), pytest (185 passed).
- `feature/remove-redis` (from develop, uncommitted): Redis task queue removed (worker, task handlers, envelope/result, Redis client, settings, readiness component, fakeredis tests, compose service, `docs/redis-task-queue.md`). REST is the only transport; kalibra-api calls extraction/generation synchronously. Gates: ruff, mypy, import-linter, pytest 168 passed.
- 2026-11-11 correction: teacher generation with already-ingested material reran successfully for refreshed desktop evidence. Mistral scenarios remain pending without a key; original native BKT evidence was preserved. No engine source changes; correction worker/Redis/cloned data removed.
- 2026-11-11 functional QA: real generation/verification with already-ingested local materials and BKT updates through the API/iOS passed. Mistral success/error scenarios explicitly pending without an API key; new discard/regeneration was not observed as a controlled test. No source changes; isolated QA workers/Redis removed.
- Three bounded contexts (`mastery`, `generation`, `verification`) implemented and merged in `develop`.
- Branch `feature/openapi-docs-and-readiness` (not merged, not pushed): OpenAPI grouped by tags
  (`Mastery`, `Generation`, `Extraction`, `Health`) with examples and documented errors; readiness
  with only the two provider keys; extraction 422/502 fix.
- Gates green on that branch: ruff, mypy strict, import-linter, pytest (189 tests, ~99 % coverage).

## Decisions (and why)
- Generated statements are direct questions: the prompt forbids citing the material/syllabus/unit, and `strip_source_lead_in` removes a leading source clause ("De acuerdo con el material ..., ") because students never see the material. Any statement code must be one fenced Markdown block with its language.
- Capabilities read cached settings independently of readiness and always return 200; an empty Mistral key disables platform material upload, and setting it plus restarting re-enables extraction without code changes. API/Web guards remain in their own repositories.
- `GenerationRun.start` prioritizes the command's explicit difficulty over the mastery target supplied by application; this preserves existing policy injection and applies the same target to generation and verification. Pool/refill and HARD→MEDIUM fallback belong to kalibra-api.
- Structured drafts require 2–5 steps and a nonempty takeaway; the prompt requests short Spanish titles, ≤2 sentences per detail, raw CODE snippets and plain-math FORMULA details. The ACL joins details with a blank line for `explanation`; legacy drafts without steps become one TEXT step and an empty `keyIdea`. Verification is unchanged.
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
- No queue: a second transport duplicated every use case and needed its own retry/delivery logic; the API's reconciliation job already retries pending extraction.
- The app version comes from package metadata (`engine_version()` in `main.py`), `0.0.0` fallback.
- Missing provider keys never fail boot: the lifespan logs one warning per key.

## Lessons learned and mistakes to avoid
- import-linter's logging config (run by `tests/architecture`) disables loggers created before it;
  tests that assert on engine logs must re-enable the logger (see `tests/shared/test_lifespan.py`).
- A Mistral `400` cannot be told apart from an engine misconfiguration (e.g. a wrong
  `MISTRAL_OCR_MODEL`) without parsing the provider body; today it counts as a bad material.
- `docker compose config` prints every variable of the local `.env`: do not paste its output.

## Next steps (to operate the MVP)
- Merge the feature branch into `develop` after review; add `ProblemDetails` to the class diagram.
- Open questions for the user: 409 is mapped but unreachable from the generation loop; a provider
  failure in one run of a multi-exercise request discards the attempts of the other runs.
