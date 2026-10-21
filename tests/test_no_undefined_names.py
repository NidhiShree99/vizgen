"""
Static check for undefined names across the codebase.

The render smoke tests only execute code paths that run on page
load. A name used solely inside a button handler — say a solver
imported for the Optimize button — can go missing in a refactor and
stay invisible until a user clicks it. pyflakes catches that class
of bug cheaply, so it runs as part of the suite.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODULES = [
    "app.py",
    "ai.py", "charts.py", "db.py", "filters.py",
    "optimizer.py", "owner.py", "pdf_export.py", "quota.py",
    "ui/config.py", "ui/helpers.py", "ui/home.py", "ui/share.py",
    "ui/sidebar.py", "ui/state.py", "ui/styles.py",
    "ui/builder/ai_tools.py", "ui/builder/canvas.py",
    "ui/builder/data.py", "ui/builder/generators.py",
    "ui/builder/history.py", "ui/builder/page.py",
    "ui/builder/refresh.py", "ui/builder/topbar.py",
]


def _pyflakes(path):
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", path],
        cwd=ROOT, capture_output=True, text=True)
    return [
        line for line in result.stdout.splitlines()
        if "undefined name" in line
    ]


@pytest.mark.parametrize("module", MODULES)
def test_module_has_no_undefined_names(module):
    pytest.importorskip("pyflakes")
    problems = _pyflakes(module)
    assert not problems, "\n".join(problems)
