# Installing & Running Pre-commit

This repository uses `pre-commit` to enforce code quality through automated formatting, linting, and type checking.

## Installation

### 1. Install Dependencies

```bash
# Install poetry dependencies (includes pre-commit, ruff, mypy)
poetry install --with dev

# Or install manually if not using poetry
pip install pre-commit ruff mypy
```

### 2. Install Pre-commit Hooks

```bash
# Install the git hooks (run this once after cloning)
poetry run pre-commit install

# Or if using system python
pre-commit install
```

## Usage

### Automatic Execution

Pre-commit hooks will automatically run on every `git commit`. If any hooks fail, the commit will be blocked until you fix the issues.

### Manual Execution

```bash
# Run all hooks on all files
poetry run pre-commit run --all-files

# Run specific hook
poetry run pre-commit run ruff --all-files
poetry run pre-commit run ruff-format --all-files

# Run on specific files
poetry run pre-commit run --files packages/example-package/src/example_package/__init__.py
```

### Bypassing Hooks (Not Recommended)

```bash
# Skip pre-commit hooks (emergency use only)
git commit --no-verify -m "emergency commit"
```

## Configured Tools

### Ruff (Linting & Formatting)
- **Purpose**: Python linting and code formatting
- **Auto-fixes**: Many issues are automatically fixed
- **Configuration**: See `[tool.ruff]` in `pyproject.toml`

### MyPy (Type Checking)
- **Purpose**: Static type checking for Python
- **Status**: Currently disabled due to monorepo complexity
- **Note**: MyPy has issues with duplicate module names in monorepos

### Standard Hooks
- `check-yaml`: Validates YAML files
- `end-of-file-fixer`: Ensures files end with newline
- `trailing-whitespace`: Removes trailing whitespace
- `check-merge-conflict`: Detects merge conflict markers
- `check-added-large-files`: Prevents large files from being committed

## Common Issues & Solutions

### Pre-commit Not Running
```bash
# Reinstall hooks if they don't run
poetry run pre-commit uninstall
poetry run pre-commit install
```

### Ruff Errors
Most ruff errors can be auto-fixed:
```bash
poetry run ruff check --fix packages/
poetry run ruff format packages/
```

### File Modified by Hooks
If hooks modify files (auto-formatting), you need to re-add and commit:
```bash
git add .
git commit -m "your message"
```

### Performance
For faster execution on large repositories:
```bash
# Run only on staged files
poetry run pre-commit run

# Skip slow hooks for quick commits
SKIP=mypy git commit -m "quick fix"
```

## CI Integration

Pre-commit also runs in GitHub Actions on every pull request. PRs cannot be merged unless all hooks pass.

See `.github/workflows/pre-commit-checks.yml` for CI configuration.
