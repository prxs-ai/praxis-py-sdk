# Monorepo for Praxis SDK

This repository contains multiple standalone Python services, each organized as an individual package with its own source code, configuration, and tests.

## Project Structure

Example structure of a single service (`s3-service`):

```
s3-service/
├── src/
│   └── s3_service/
│       ├── __init__.py
│       ├── config.py
│       └── main.py
├── tests/
│   ├── __init__.py
│   └── test_s3_service.py
├── pyproject.toml
├── poetry.lock
└── README.md
```

* `src/` — contains the main application code.
* `tests/` — includes unit and integration tests.
* `pyproject.toml` — defines the package configuration (managed with Poetry).
* `README.md` — service-level documentation.

## Requirements

* Python 3.10+
* [Poetry](https://python-poetry.org/) for dependency management

## Installation

```bash
poetry install
```

## Running Tests

```bash
poetry run pytest
```

## Adding New Services

To add a new service, replicate the structure of `s3-service` and update the root documentation as needed.
