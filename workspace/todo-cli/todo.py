#!/usr/bin/env python3
"""todo.py — 一个简单的命令行 TODO 管理器。

用法:
    python todo.py add "买牛奶"
    python todo.py list [--all]
    python todo.py done <id>
    python todo.py rm <id>

数据保存在 todo.json（默认与脚本同目录，可用 TODO_FILE 环境变量覆盖）。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 数据文件路径：默认脚本同目录下 todo.json，可用环境变量 TODO_FILE 覆盖
DATA_FILE = Path(os.environ.get("TODO_FILE", Path(__file__).parent / "todo.json"))


def load_todos() -> list[dict]:
    """从 JSON 文件加载待办列表。文件不存在或损坏时返回空列表。"""
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_todos(todos: list[dict]) -> None:
    """将待办列表写入 JSON 文件。"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def next_id(todos: list[dict]) -> int:
    """返回下一个可用的 id（当前最大 id + 1）。"""
    return max((t.get("id", 0) for t in todos), default=0) + 1


def cmd_add(todos: list[dict], title: str) -> None:
    """添加一条待办。"""
    todo = {
        "id": next_id(todos),
        "title": title,
        "done": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    todos.append(todo)
    save_todos(todos)
    print(f"✓ 已添加: [{todo['id']}] {title}")


def cmd_list(todos: list[dict], show_all: bool = False) -> None:
    """列出待办事项。默认只显示未完成；--all 显示全部。"""
    if not todos:
        print("（暂无待办事项）")
        return

    shown = todos if show_all else [t for t in todos if not t.get("done")]
    if not shown:
        print("（没有未完成的待办，使用 --all 查看全部）")
        return

    print("待办事项:")
    for t in shown:
        mark = "✓" if t.get("done") else " "
        print(f"  [{mark}] {t['id']:>3}  {t['title']}")


def cmd_done(todos: list[dict], todo_id: int) -> None:
    """将指定 id 的待办标记为完成。"""
    for t in todos:
        if t["id"] == todo_id:
            if t.get("done"):
                print(f"ℹ [{todo_id}] 已经是完成状态: {t['title']}")
            else:
                t["done"] = True
                save_todos(todos)
                print(f"✓ 已完成: [{todo_id}] {t['title']}")
            return
    print(f"✗ 找不到 id 为 {todo_id} 的待办", file=sys.stderr)
    sys.exit(1)


def cmd_rm(todos: list[dict], todo_id: int) -> None:
    """删除指定 id 的待办。"""
    for i, t in enumerate(todos):
        if t["id"] == todo_id:
            removed = todos.pop(i)
            save_todos(todos)
            print(f"🗑 已删除: [{removed['id']}] {removed['title']}")
            return
    print(f"✗ 找不到 id 为 {todo_id} 的待办", file=sys.stderr)
    sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo",
        description="简单的命令行 TODO 管理器",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="添加待办")
    p_add.add_argument("title", help="待办内容")

    p_list = sub.add_parser("list", help="列出待办")
    p_list.add_argument("--all", action="store_true", help="显示全部（含已完成）")

    p_done = sub.add_parser("done", help="标记完成")
    p_done.add_argument("id", type=int, help="待办 id")

    p_rm = sub.add_parser("rm", help="删除待办")
    p_rm.add_argument("id", type=int, help="待办 id")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    todos = load_todos()

    if args.command == "add":
        cmd_add(todos, args.title)
    elif args.command == "list":
        cmd_list(todos, args.all)
    elif args.command == "done":
        cmd_done(todos, args.id)
    elif args.command == "rm":
        cmd_rm(todos, args.id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
