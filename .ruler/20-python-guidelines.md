# Python coding guidelines

## Core Requirements
- Python 3.13+
- `pyproject.toml` only (NO `setup.py`)
- Build backend: `flit`
- `src/` layout for packages

## Type Safety
- Type all functions and classes
- Use `from __future__ import annotations`
- Tools: `mypy --strict`, `ruff`

## Style
- f-strings, `pathlib.Path`, dataclasses
- Context managers for resources
- No bare `except:` or `print()`
- `logging` module for output

## Dependencies
- Manage with `uv` or `pip-tools`
- Pin versions in `pyproject.toml`
- Separate dev/runtime deps

## Testing
- `pytest` + `pytest-asyncio`
- Tests in `tests/` mirroring source

## Modern Features
- `match/case`, `async/await`, `functools.cache`
- `enum.Enum` for constants
- Type hints as primary documentation