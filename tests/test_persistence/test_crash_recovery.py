
import subprocess
import sys


def test_real_crash_recovery():

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.demo_real_crash",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        result.stdout + "\n" + result.stderr
    )

    assert (
        "CRASH RECOVERY TEST PASSED"
        in result.stdout
    )

    assert "Planner calls: 1" in result.stdout
    assert "Researcher calls: 2" in result.stdout
    assert "Writer calls: 1" in result.stdout
