"""Locate the required source checkout for editable and ordinary installations.

The UI and reviewed reference data live in the checkout. Resolve once on import
so subsequent temporary working-directory changes do not change their identity.
"""
from pathlib import Path


def _checkout():
    candidates = [Path(__file__).resolve().parents[2], Path.cwd(), *Path.cwd().parents]
    for candidate in candidates:
        if (candidate / 'pyproject.toml').is_file() and (candidate / 'src/polytoken').is_dir() and (candidate / 'web/index.html').is_file():
            return candidate
    raise RuntimeError('Run PolyToken from its source checkout; web assets and reviewed reference data are required.')


ROOT = _checkout()
