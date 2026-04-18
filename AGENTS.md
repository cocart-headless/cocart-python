# CoCart Python SDK

Official Python SDK for the CoCart REST API.

- **Package:** `cocart`
- **Version:** 1.0.0
- **Distribution:** PyPI
- **License:** MIT
- **Supports:** Python 3.9 – 3.13

---

## Commands

```bash
pip install -e ".[dev]"                              # install with dev dependencies
pip install -e .                                     # install without dev dependencies
python -m pytest                                     # run all tests
python -m pytest -v                                  # run tests (verbose)
python -m pytest tests/test_cocart.py               # run a single test file
python -m pytest tests/test_cocart.py::TestConstructor::test_default_options  # run a single test
pytest --cov=src/cocart --cov-report=html           # run tests with coverage
ruff check src/ tests/                              # lint
ruff format src/ tests/                             # format
mypy src/                                           # type-check
python -m build                                     # build distribution (hatchling)
```

---

## Tech Stack

| | |
|---|---|
| Language | Python 3.9+ |
| Build backend | hatchling (configured in `pyproject.toml`) |
| Tests | pytest 7+ with pytest-cov 4+ |
| Type checker | mypy 1.0+ (strict mode) |
| Linter / formatter | ruff 0.1+ |
| HTTP (default) | requests 2.28+ |
| HTTP (optional) | httpx 0.24+ |
| Config | all in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`) |

---

## Project Structure

```
src/cocart/
  __init__.py          # public exports
  cocart.py            # main CoCart client class
  response.py          # Response wrapper
  session_manager.py   # session lifecycle
  jwt_manager.py       # JWT authentication
  endpoints/           # cart, products, sessions, store
  exceptions/          # CoCartException and subclasses
  http/                # HTTP adapters (requests, httpx, abstract interface)
  storage/             # MemoryStorage, FileStorage
  validation.py        # input validators
tests/
  conftest.py          # pytest fixtures
  mock_http_adapter.py # mock HTTP adapter
  test_cocart.py
  test_cart.py
  test_products.py
  ...
```

---

## Code Style

- **File names:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions, methods, variables:** `snake_case`
- **Line length:** 120 characters (ruff config)
- **Type hints:** required on all public methods; mypy strict mode
- All tool configuration lives in `pyproject.toml` — do not create separate `.ruff.toml`, `pytest.ini`, or `.mypy.ini`

---

## Git

- **Commit style:** Imperative, capital first letter — `Add X`, `Added X`, `Fix X`
- **Co-author footer:** `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

---

## Testing

| | |
|---|---|
| Framework | pytest 7+ |
| Location | `tests/` |
| File pattern | `test_*.py` |
| Mocking | `MockHttpAdapter` in `tests/mock_http_adapter.py` |
| Fixtures | `tests/conftest.py` |
| Coverage | `pytest --cov=src/cocart --cov-report=html` |

Test classes use `class TestX:` grouping with `def test_*` methods. No real HTTP calls in tests.
