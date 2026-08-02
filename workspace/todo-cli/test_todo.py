#!/usr/bin/env python3
"""对 todo.py 的端到端自动化验证脚本。"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "todo.py"


def run(*args, data_file):
    env = dict(os.environ)
    env["TODO_FILE"] = str(data_file)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main():
    passed = 0
    failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}  {detail}")

    with tempfile.TemporaryDirectory() as tmp:
        data_file = Path(tmp) / "todo.json"

        print("1) 空列表")
        rc, out, _ = run("list", data_file=data_file)
        check("空列表返回成功", rc == 0)
        check("显示暂无提示", "暂无待办" in out, out)

        print("2) 添加")
        rc, out, _ = run("add", "买牛奶", data_file=data_file)
        check("添加返回成功", rc == 0, f"rc={rc}")
        check("提示已添加", "已添加" in out, out)
        run("add", "写周报", data_file=data_file)
        run("add", "锻炼30分钟", data_file=data_file)

        print("3) 列出（默认只显示未完成）")
        rc, out, _ = run("list", data_file=data_file)
        check("list返回成功", rc == 0)
        check("显示3条未完成", out.count("]") >= 3 and "写周报" in out, out)

        print("4) 标记完成")
        rc, out, _ = run("done", "2", data_file=data_file)
        check("done返回成功", rc == 0, f"rc={rc}")
        check("提示已完成", "已完成" in out, out)
        rc, out, _ = run("list", data_file=data_file)
        check("完成后默认列表少一条", "写周报" not in out, out)
        rc, out, _ = run("list", "--all", data_file=data_file)
        check("--all仍显示已完成项", "写周报" in out, out)

        print("5) 删除")
        rc, out, _ = run("rm", "1", data_file=data_file)
        check("rm返回成功", rc == 0, f"rc={rc}")
        check("提示已删除", "已删除" in out, out)
        rc, out, _ = run("list", "--all", data_file=data_file)
        check("删除后不再显示", "买牛奶" not in out, out)

        print("6) 错误处理")
        rc, out, err = run("done", "999", data_file=data_file)
        check("不存在的id报错", rc != 0 and "找不到" in err, f"rc={rc} err={err}")
        rc, out, err = run("rm", "999", data_file=data_file)
        check("删除不存在的id报错", rc != 0, f"rc={rc}")

        # 验证 JSON 数据确实落盘且可读
        from todo import load_todos
        todos = load_todos.__wrapped__ if hasattr(load_todos, "__wrapped__") else None
        # 直接用文件验证
        import json
        with open(data_file, encoding="utf-8") as f:
            raw = json.load(f)
        check("JSON数据可解析", isinstance(raw, list))

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
