# Contributing to Praxis SDK

We appreciate your interest in contributing to the Praxis SDK! This document outlines our development workflow and contribution guidelines.

## GitHub Flow

We follow the [GitHub Flow](https://guides.github.com/introduction/flow/) branching model for all contributions:

1. **Create a branch** from `main` for your feature or fix
2. **Make commits** to your branch with descriptive messages
3. **Open a pull request** early to discuss your changes
4. **Make revisions** based on feedback
5. **Merge** your branch after approval

### Branch Naming Convention

Use descriptive branch names that indicate the purpose of your changes:
- `feature/add-authentication`
- `fix/memory-leak-in-parser`
- `docs/update-installation-guide`
- `refactor/simplify-config-loading`

### Commit Messages

Write clear, concise commit messages:
- Use the imperative mood ("Add feature" not "Added feature")
- Keep the first line under 50 characters
- Include a detailed description if necessary

### Branch Protection Rules

The `main` branch is protected with the following requirements:
- **Pull request reviews**: At least 1 approval required
- **Status checks**: All CI tests must pass
- **Up-to-date**: Branch must be up-to-date with `main` before merging
- **Linear history**: Enforce linear history (no merge commits)

## Development Setup

1. Fork the repository
2. Clone your fork locally
3. Install dependencies: `poetry install`
4. Create a new branch: `git checkout -b feature/your-feature`
5. Make your changes
6. Run tests: `poetry run pytest`
7. Run linting: `poetry run ruff check`
8. Run type checking: `python scripts/run_mypy.py`

## Pull Request Process

1. **Before submitting**, ensure your PR:
   - Has a clear title and description
   - Includes tests for new functionality
   - Updates documentation if needed
   - Passes all CI checks

2. **Use the PR template** and complete all checklist items

3. **Request review** from at least one maintainer

4. **Respond to feedback** promptly and make requested changes

5. **Squash and merge** once approved (maintainers will handle this)

## Code Standards

- Follow PEP 8 for Python code style
- Use type hints for all functions and methods
- Write docstrings for public functions
- Keep functions small and focused
- Add tests for new features and bug fixes

## Testing

- Write unit tests in the `tests/` directory
- Use descriptive test names that explain what is being tested
- Aim for high test coverage
- Run the full test suite before submitting PRs

## Documentation

- Update relevant documentation for user-facing changes
- Use clear, concise language
- Include code examples where helpful
- Keep the README.md up to date

## Getting Help

- Check existing issues and PRs first
- Ask questions in GitHub Discussions
- Tag maintainers for urgent issues
- Be patient and respectful in all interactions

Thank you for contributing to Praxis SDK!
