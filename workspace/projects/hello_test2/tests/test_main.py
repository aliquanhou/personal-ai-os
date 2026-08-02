import subprocess
import sys


def test_main_output():
    """验证 src/main.py 输出 'Hello AI OS'"""
    result = subprocess.run(
        [sys.executable, "src/main.py"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "Hello AI OS"
