import ast
import pathlib
import sys

import auto_invest.rubric

FORBIDDEN = {"nautilus_trader", "AlgorithmImports", "QuantConnect", "pandas", "numpy"}


def imported_names(path: pathlib.Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, 0
        elif isinstance(node, ast.ImportFrom):
            yield node.module or "", node.level


def test_rubric_imports_only_stdlib_and_itself():
    package = pathlib.Path(auto_invest.rubric.__file__).parent
    for path in package.glob("*.py"):
        for name, level in imported_names(path):
            top = name.split(".")[0]
            assert top not in FORBIDDEN, f"{path.name} imports {name}"
            assert top != "auto_invest" or name.startswith("auto_invest.rubric"), (
                f"{path.name} imports {name}"
            )
            assert level > 0 or top in sys.stdlib_module_names or name.startswith(
                "auto_invest.rubric"
            ), f"{path.name} imports {name}, which is not standard library"


def test_rubric_version_is_a_string():
    assert isinstance(auto_invest.rubric.RUBRIC_VERSION, str)
    assert auto_invest.rubric.RUBRIC_VERSION
