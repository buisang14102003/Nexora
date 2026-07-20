# Task 1 report: Bootstrap local runtime and test foundation

## Implementation summary

- Added Python 3.11 project metadata with the FastAPI, settings, Uvicorn, pytest, and HTTP test-client dependencies.
- Added the cached `Settings` interface and the minimum FastAPI health endpoint: `GET /healthz` returns `{"status": "ok"}`.
- Added a local-only Compose stack for PostgreSQL, MinIO, Qdrant, API, worker, Chainlit, and self-hosted Langfuse (PostgreSQL, ClickHouse, Redis, web, and worker). Every published port binds to `127.0.0.1`; API and worker use `http://host.docker.internal:11434` for Ollama.
- Added the required environment-secret template, safe ignore rules, test foundation, and executable Ollama model-pull script.

## Files changed

- `.gitignore`
- `.env.example`
- `pyproject.toml`
- `compose.yaml`
- `app/core/config.py`
- `app/api/main.py`
- `tests/conftest.py`
- `tests/test_health.py`
- `scripts/pull_models.sh`

## RED / GREEN evidence

The host did not have `pytest` installed initially (`zsh: command not found: pytest`), so I created the ignored local Python 3.11 virtual environment from the declared project dependencies. The actual RED run was then:

```text
$ .venv/bin/pytest tests/test_health.py -v
E   ModuleNotFoundError: No module named 'app'
========================= 1 warning, 1 error in 0.49s =========================
```

This failed for the expected missing application module. After adding the configuration module and endpoint, the GREEN run was:

```text
$ .venv/bin/pytest tests/test_health.py -v
tests/test_health.py::test_healthz_returns_ok PASSED
============================== 1 passed in 0.18s ===============================
```

Focused container validation:

```text
$ .venv/bin/pytest tests/test_health.py -v && docker compose config --quiet
tests/test_health.py::test_healthz_returns_ok PASSED
============================== 1 passed in 0.18s ===============================
```

`docker compose config --quiet` exited 0 with no unset-variable warnings.

## Full-suite result

```text
$ .venv/bin/pytest -q
.                                                                        [100%]
1 passed in 0.18s
```

Additional checks passed: `git diff --check`, `docker compose config --quiet`, `sh -n scripts/pull_models.sh`, executable-bit check for the model script, and importing `app.api.main` from outside the repository root.

## Self-review

- Required interfaces match the brief exactly: `Settings`, cached `get_settings()`, exported `app`, and `/healthz` response.
- Compose contains all required core services and a self-hosted Langfuse stack; PostgreSQL, MinIO, Qdrant, and Langfuse data use named volumes.
- All exposed ports are explicitly loopback-bound. API and worker both set the required Ollama host URL and default model IDs.
- `.env.example` lists the required secrets without values, and `.gitignore` excludes local environment files while retaining the template.
- `scripts/pull_models.sh` invokes exactly `ollama pull gemma3:4b` and `ollama pull qwen3-embedding:0.6b`.

## Concerns

- Before `docker compose up`, the operator must copy `.env.example` to `.env` and replace each blank secret with a strong local value. The configuration validator intentionally permits blank values so `docker compose config` can render without exposing or committing secrets; stateful services will reject unsafe blank credentials at startup.
- API, worker, and Chainlit commands refer to application entry points introduced by later planned tasks, so only the API health endpoint is runnable in this bootstrap task.

## Review-fix report (2026-07-20)

### Changes made

- Added the minimal long-running `worker/main.py` and minimal `chainlit_app.py` entry points, plus the Chainlit dependency.
- Configured setuptools to package both application packages and `chainlit_app.py`; this makes the existing Compose `pip install .` commands install successfully after adding `worker/`.
- Added `scripts/validate_env.py`; it rejects blank `DATABASE_URL`, PostgreSQL, MinIO, JWT, and Langfuse values with their variable names.
- Added the `validate-env` Compose service and `service_completed_successfully` gates for PostgreSQL, MinIO, API, worker, Chainlit, and Langfuse PostgreSQL/web/worker. `.env.example` now documents the manual validation command.
- Made `Settings` reject blank `DATABASE_URL` values.
- Added regression coverage for the settings validation, entry-point imports, package build, and clear environment-validation failures.

### RED evidence

```text
$ .venv/bin/pytest tests/test_config.py tests/test_entrypoints.py tests/test_validate_env.py -v
tests/test_config.py::test_settings_rejects_blank_database_url FAILED
tests/test_entrypoints.py::test_runtime_entrypoints_are_importable[worker.main] FAILED
tests/test_entrypoints.py::test_runtime_entrypoints_are_importable[chainlit_app] FAILED
tests/test_validate_env.py::test_validate_env_reports_blank_required_values FAILED
============================== 4 failed in 0.14s ===============================

$ .venv/bin/pytest tests/test_entrypoints.py::test_package_builds_with_runtime_entrypoints -v
tests/test_entrypoints.py::test_package_builds_with_runtime_entrypoints FAILED
error: Multiple top-level packages discovered in a flat-layout: ['app', 'worker'].
============================== 1 failed in 1.67s ===============================
```

### Final verification

```text
$ .venv/bin/pytest -v
tests/test_config.py::test_settings_rejects_blank_database_url PASSED
tests/test_entrypoints.py::test_runtime_entrypoints_are_importable[worker.main] PASSED
tests/test_entrypoints.py::test_runtime_entrypoints_are_importable[chainlit_app] PASSED
tests/test_entrypoints.py::test_package_builds_with_runtime_entrypoints PASSED
tests/test_health.py::test_healthz_returns_ok PASSED
tests/test_validate_env.py::test_validate_env_reports_blank_required_values PASSED
========================= 6 passed, 1 warning in 2.58s =========================
```

The sole warning is emitted by Chainlit's transitive `traceloop` dependency: `PydanticDeprecatedSince20` for its class-based configuration.

```text
$ worker placeholder start check and Chainlit HTTP start check
worker placeholder start check: passed
chainlit HTTP start check: passed

$ env -i PATH="$PATH" .venv/bin/python scripts/validate_env.py --env-file .env.example
Set non-empty values in .env before starting Docker: DATABASE_URL, POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, JWT_SECRET, LANGFUSE_POSTGRES_PASSWORD, LANGFUSE_NEXTAUTH_SECRET, LANGFUSE_SALT, LANGFUSE_ENCRYPTION_KEY

$ DATABASE_URL='postgresql+psycopg://rag:test@postgres:5432/rag' POSTGRES_PASSWORD=test MINIO_ROOT_PASSWORD=test JWT_SECRET=test LANGFUSE_POSTGRES_PASSWORD=test LANGFUSE_NEXTAUTH_SECRET=test LANGFUSE_SALT=test LANGFUSE_ENCRYPTION_KEY=test .venv/bin/python scripts/validate_env.py --env-file .env.example
Environment validation passed.

$ DATABASE_URL='postgresql+psycopg://rag:test@postgres:5432/rag' POSTGRES_PASSWORD=test MINIO_ROOT_PASSWORD=test JWT_SECRET=test LANGFUSE_POSTGRES_PASSWORD=test LANGFUSE_NEXTAUTH_SECRET=test LANGFUSE_SALT=test LANGFUSE_ENCRYPTION_KEY=test docker compose config --quiet
exit 0

$ git diff --check
exit 0
```

### Remaining concern

- The Chainlit package's current transitive dependency emits the warning noted above; application tests and its local HTTP start check pass.

## Review-fix: validation gates for Qdrant, ClickHouse, and Redis (2026-07-20)

### Changes made

- Added `validate-env` `service_completed_successfully` dependencies to Qdrant, ClickHouse, and Redis, preventing those services from starting after environment validation fails.
- Added a focused Compose regression test covering all three dependencies.

### RED / GREEN evidence

Before the Compose change, the focused regression failed for each ungated service:

```text
$ .venv/bin/pytest tests/test_compose.py -v
tests/test_compose.py::test_stateful_services_wait_for_environment_validation[qdrant] FAILED
tests/test_compose.py::test_stateful_services_wait_for_environment_validation[clickhouse] FAILED
tests/test_compose.py::test_stateful_services_wait_for_environment_validation[redis] FAILED
============================== 3 failed in 0.02s ===============================
```

After the change:

```text
$ .venv/bin/pytest tests/test_compose.py -v
============================== 3 passed in 0.01s ===============================

$ DATABASE_URL='postgresql+psycopg://rag:test@postgres:5432/rag' POSTGRES_PASSWORD=test MINIO_ROOT_PASSWORD=test JWT_SECRET=test LANGFUSE_POSTGRES_PASSWORD=test LANGFUSE_NEXTAUTH_SECRET=test LANGFUSE_SALT=test LANGFUSE_ENCRYPTION_KEY=test docker compose config --quiet
exit 0

$ .venv/bin/pytest -v
========================= 9 passed, 1 warning in 2.68s =========================

$ git diff --check
exit 0
```

The one warning remains Chainlit's transitive `traceloop` Pydantic deprecation warning described above.
