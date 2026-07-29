"""The gap this closes: pytest puts each test file's directory on sys.path, so a
module with a bad import style can pass 460 tests and still fail to start in the
container, where /app is the only root. That happened on 2026-07-29 — a wrongly
scoped `from model_config import …` shipped green and crashed the first Cloud Run
revision on boot.

This asserts the package imports the way the RUNTIME imports it: absolute from the
repo root, no per-file sys.path help.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

MODULES = [
    "backend.main",
    "backend.agents.soap",
    "backend.agents.followup",
    "backend.voice.gemini_live_adapter",
    "backend.model_config",
]


def test_entrypoint_modules_import_from_repo_root_only():
    """Import each runtime module in a clean interpreter whose only path entry is
    the repo root — the container's condition, not pytest's."""
    for mod in MODULES:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            f"{mod} fails to import as the runtime imports it "
            f"(this is what breaks the container while tests stay green):\n{proc.stderr[-800:]}"
        )
