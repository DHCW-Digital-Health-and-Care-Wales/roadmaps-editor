"""A `noqa` says why: `# noqa: <codes> - <reason>`.

Ruff has no rule that asks for a reason. Added 2026-11-28: bare suppressions passed
lint and reached review in two deliveries (PRs #344 and #346). Review by 2027-02-26.
"""

import os
import re
import tokenize
from collections.abc import Iterator
from io import StringIO
from pathlib import Path
from typing import Final

import pytest

API_DIR: Final = Path(__file__).resolve().parents[1]
# `noqa`, and Ruff's own `ignore`, `file-ignore` and `disable` comments, which fail with
# or without a reason. isort's action comments (`isort: off`) are not covered.
SUPPRESSION: Final = re.compile(
    r"#\s*(?:(?:ruff|flake8)\s*:\s*)?noqa\b|#\s*ruff\s*:\s*(?:file-)?(?:ignore|disable)\b",
    re.IGNORECASE,
)
REASONED: Final = re.compile(
    r"#\s*(?:(?:ruff|flake8)\s*:\s*)?noqa\s*:\s*[A-Z]+\d+(?:[\s,]+[A-Z]+\d+)*\s+-\s+\S",
    re.IGNORECASE,
)


def unreasoned(source: str) -> Iterator[int]:
    """The lines whose comment suppresses a rule without the one reasoned form."""
    for token in tokenize.generate_tokens(StringIO(source).readline):
        if token.type == tokenize.COMMENT and any(
            not REASONED.match(token.string, found.start())
            for found in SUPPRESSION.finditer(token.string)
        ):
            yield token.start[0]


def python_files() -> Iterator[Path]:
    for directory, subdirectories, names in os.walk(API_DIR):
        # Not the API's own: the environment, tool caches and installed packages.
        subdirectories[:] = [
            name for name in subdirectories if not name.startswith(".") and name != "node_modules"
        ]
        yield from (Path(directory, name) for name in names if name.endswith(".py"))


@pytest.mark.parametrize(
    ("source", "lines"),
    [
        pytest.param("import os  # noqa: F401 - re-exported\n", [], id="reasoned"),
        pytest.param("import os  # noqa: F401, E501 - re-exported\n", [], id="two codes"),
        pytest.param("# ruff: noqa: F401 - re-exported\n", [], id="reasoned whole file"),
        pytest.param('PLANTED = "# noqa: F401"\n', [], id="in a string"),
        pytest.param("import os  # noqa: F401\n", [1], id="codes alone"),
        pytest.param("import os  # noqa: F401 re-exported\n", [1], id="no separator"),
        pytest.param("import os  # noqa: F401 - \n", [1], id="empty reason"),
        pytest.param("import os  # NOQA\n", [1], id="blanket"),
        pytest.param("# ruff: noqa: F401\nimport os\n", [1], id="whole file"),
        pytest.param("import os  # ruff: ignore[F401]\n", [1], id="ruff ignore"),
        pytest.param("# ruff: file-ignore[F401]\n", [1], id="ruff file-ignore"),
        pytest.param("# ruff: disable[F401]\n# ruff: enable[F401]\n", [1], id="ruff range"),
    ],
)
def test_only_a_reasoned_noqa_passes(source: str, lines: list[int]) -> None:
    assert list(unreasoned(source)) == lines


def test_every_suppression_in_the_api_gives_its_reason() -> None:
    found = [
        f"{path.relative_to(API_DIR)}:{line}: write `# noqa: <codes> - <reason>`, "
        "or fix what the rule reports"
        for path in python_files()
        for line in unreasoned(path.read_text(encoding="utf-8"))
    ]

    assert sorted(found) == []
