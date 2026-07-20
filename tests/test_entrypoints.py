import importlib
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("module_name", ["worker.main", "chainlit_app"])
def test_runtime_entrypoints_are_importable(module_name: str) -> None:
    assert importlib.import_module(module_name)


def test_package_builds_with_runtime_entrypoints(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", ".", "--wheel-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
