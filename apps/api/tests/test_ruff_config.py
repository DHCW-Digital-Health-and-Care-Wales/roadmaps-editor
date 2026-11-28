"""Ruff fails an import of a name another package keeps private (PLC2701).

The rule is a preview rule: a config that loses `preview` only warns and passes, so this
holds the wiring in `pyproject.toml`.
"""

import subprocess
import sys
from pathlib import Path
from typing import Final

API_DIR: Final = Path(__file__).resolve().parents[1]


def test_ruff_fails_an_import_of_a_private_name() -> None:
    result = subprocess.run(  # noqa: S603 - the test's own interpreter and arguments
        [
            sys.executable,
            *("-m", "ruff", "check", "--no-cache", "--output-format=json"),
            *("--stdin-filename", "src/roadmaps_api/planted.py", "-"),
        ],
        cwd=API_DIR,
        input="from fastapi.routing import _effective_route_context_var\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert '"PLC2701"' in result.stdout
