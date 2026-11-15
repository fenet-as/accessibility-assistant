"""Run VoiceRecorder node tests when node is available."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / "tests" / "js" / "voice_recorder.test.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_voice_recorder_node_suite():
    result = subprocess.run(
        ["node", "--test", str(TEST_FILE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            "VoiceRecorder node tests failed:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
