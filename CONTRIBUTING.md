# Contributing

Thank you for your interest in the Vitality Engagement Intelligence Engine.

This repository is primarily a portfolio and demonstration project built around fully synthetic data. Contributions that improve reproducibility, documentation, testing, governance, monitoring, or maintainability are welcome.

## Development setup

Use Python 3.12 and install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

## Quality gate

Before submitting a change, run:

```powershell
ruff format --check .
ruff check .
mypy
pytest -q
pre-commit run --all-files
git diff --check
```

## Contribution expectations

- Keep changes focused and documented.
- Add or update tests when behaviour changes.
- Preserve the synthetic-data boundary.
- Do not introduce real personal, health, clinical, or confidential data.
- Do not weaken monitoring, governance, drift, suppression, or human-review controls merely to make checks pass.
- Preserve the distinction between the selected Python model and the separate BigQuery comparison baseline.
- Keep operational decisions subject to explicit human review.

## Pull requests

Pull requests should explain the purpose of the change, the validation performed, and any impact on model behaviour, monitoring, governance, reproducibility, or documentation.

All repository quality checks should pass before merge.
