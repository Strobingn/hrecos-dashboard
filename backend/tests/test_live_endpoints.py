"""Live provider check. Run with: pytest -m live -o addopts= -s"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_endpoints.py"


@pytest.mark.live
@pytest.mark.network
def test_live_station_endpoints():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        text=True,
    )
    assert completed.returncode == 0, "one or more live station parameters failed"
