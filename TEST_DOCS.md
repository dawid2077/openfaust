# OpenFaust Test Suite Documentation

## Overview

The test suite covers all core modules of OpenFaust with **64 tests** across **7 test files**, verified against Python 3.9 (and CI-ready for 3.9–3.13).

## Test Coverage

| Module | File | Tests | What's Tested |
|--------|------|-------|---------------|
| **Heartbeat** | `tests/test_heartbeat.py` | 8 | `restart_limit()`, `check_limits()`, queue orchestration, module structure |
| **Kairos Router** | `tests/test_kairos.py` | 9 | `decide()` routing (1/2/3), context handling, API failure fallback, malformed JSON, profile independence |
| **Context Builder** | `tests/test_context.py` | 12 | `context_call()` and `context_kairos()` — message formatting, timestamp annotations, empty DB, event filtering |
| **Save Messages** | `tests/test_save_messages.py` | 5 | `save_normal_message()` — row insertion, timestamps, env-based paths |
| **Tosqlite** | `tests/test_tosqlite.py` | 9 | `save()` — user/assistant row pairs, metadata storage, malformed JSON, empty choices |
| **Docker Setup** | `tests/test_dockersetup.py` | 9 | `init_db()` — directory creation, table schema, default files, idempotency |
| **Identity Get** | `tests/test_identity_get.py` | 8 | `get_companion_identity()` — API extraction, missing files, fallback, caching |

## Running Tests

```bash
cd openfaust_test
pip install pytest pytest-timeout pytest-mock
cd tests && python -m pytest -v --timeout=30
```



## CI Pipeline

Defined in `.github/workflows/tests.yml`:
- Triggers: push/PR to `main` or `dev` branches
- Matrix: Python 3.9, 3.10, 3.11, 3.12, 3.13 on ubuntu-latest
- Steps: checkout → setup Python → pip install deps → pytest
- Failure output: extended traceback on fail
