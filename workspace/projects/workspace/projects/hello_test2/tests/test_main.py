"""测试主程序输出"""
import subprocess
import sys


def test_main_output():
    """验证 src/main.py 输出 Hello AI OS"""
    result = subprocess.run(
        [sys.executable, "src/main.py"],
        capture_output=True,
        text=True,
        cwd="src/..",
    )
    assert result.returncode == 0
    assert "Hello AI OS" in result.stdout
