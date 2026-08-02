"""电商运营数字员工 v2 - CLI 入口

用法：
    python main.py init-db               # 初始化数据库
    python main.py init-data             # 生成示例数据
    python main.py setup                 # 初始化数据库 + 创建示例任务
    python main.py run --task 1          # 执行指定任务
    python main.py run-all               # 执行所有启用任务
    python main.py history               # 查看执行历史
    python main.py audit                 # 查看审计日志
    python main.py review --run 1 --task 1 --decision approved --comment "OK"
"""

import argparse
import logging
import sys

from agent import audit, runner
from db import db, models

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def cmd_init_db(args):
    path = db.init_db()
    print(f"✅ 数据库初始化完成: {path}")


def cmd_init_data(args):
    print("正在生成示例数据...")
    from generate_sample_data import main as gen
    gen()


def cmd_setup(args):
    cmd_init_db(args)
    cmd_init_data(args)
    agent = runner.EcommerceOpsAgent()
    # 创建三个示例任务（全部强制人工复核）
    agent.create_task("每日订单核对", models.TASK_TYPE_ORDER_CHECK,
                      {}, "daily:09:00", review_required=1)
    agent.create_task("库存对账", models.TASK_TYPE_STOCK_RECONCILE,
                      {"tolerance": 2}, "daily:22:00", review_required=1)
    agent.create_task("商品资料清洗", models.TASK_TYPE_PRODUCT_CLEAN,
                      {}, "daily:23:00", review_required=0)
    print("✅ 示例任务创建完成")


def cmd_run(args):
    agent = runner.EcommerceOpsAgent()
    result = agent.run_task(args.task, data_date=args.date)
    _print_result(result)


def cmd_run_all(args):
    agent = runner.EcommerceOpsAgent()
    tasks = agent.list_tasks()
    for t in tasks:
        if t["enabled"]:
            print(f"\n▶ 执行任务: {t['name']} ({t['task_type']})")
            result = agent.run_task(t["id"], data_date=args.date)
            _print_result(result)


def _print_result(result):
    status_icon = "✅" if result["status"] == "success" else "❌"
    print(f"\n{status_icon} {result['task_name']} ({result['task_type']})")
    print(f"   状态: {result['status']} | 数据日期: {result['data_date']}")
    print(f"   统计: {result['stats']}")
    print(f"   异常: {len(result['anomalies'])} 条 | 耗时: {result['duration_sec']}s")
    if result["report_path"]:
        print(f"   日报: {result['report_path']}")
    if result["anomalies"]:
        for a in result["anomalies"][:5]:
            print(f"     [{a.level}] {a.type} | {a.reference_id}: {a.detail}")


def cmd_history(args):
    agent = runner.EcommerceOpsAgent()
    records = agent.history(limit=args.limit)
    if not records:
        print("暂无历史记录")
        return
    for r in records:
        icon = "✅" if r["status"] == "success" else "❌"
        print(f"{icon} run#{r['id']} {r['task_name']} | {r['data_date']} | "
              f"异常 {r['anomaly_count']} | {r['duration_sec']}s")


def cmd_audit(args):
    entries = audit.get_recent(limit=args.limit)
    if not entries:
        print("暂无审计记录")
        return
    for e in entries:
        icon = "✅" if e["status"] == "success" else "❌"
        print(f"{icon} [{e['created_at']}] {e['action']} | {e['status']}")
        if e.get("detail"):
            print(f"     └─ {e['detail']}")


def cmd_review(args):
    agent = runner.EcommerceOpsAgent()
    rid = agent.review_run(args.run, args.task, args.decision, args.comment or "")
    print(f"✅ 复核记录已保存 (id={rid})")


def main():
    parser = argparse.ArgumentParser(description="电商运营数字员工 v2")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-db"); p.set_defaults(func=cmd_init_db)
    p = sub.add_parser("init-data"); p.set_defaults(func=cmd_init_data)
    p = sub.add_parser("setup"); p.set_defaults(func=cmd_setup)

    p = sub.add_parser("run")
    p.add_argument("--task", type=int, required=True)
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("run-all")
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_run_all)

    p = sub.add_parser("history")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("audit")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("review")
    p.add_argument("--run", type=int, required=True)
    p.add_argument("--task", type=int, required=True)
    p.add_argument("--decision", required=True,
                   choices=[models.DECISION_APPROVED, models.DECISION_MODIFIED,
                            models.DECISION_REJECTED])
    p.add_argument("--comment", default="")
    p.set_defaults(func=cmd_review)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
