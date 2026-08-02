"""电商运营数字员工 - 入口

用法：
    python main.py run                # 立即执行一次
    python main.py run --date 2026-08-03   # 指定数据日期
    python main.py schedule           # 按配置定时执行（默认每天 09:00）
    python main.py history            # 查看历史记录
    python main.py audit              # 查看审计日志
    python main.py init-data          # 生成示例数据
"""

import argparse
import logging
import time
from datetime import datetime, timedelta

from agent import config
from agent.audit import AuditLog
from agent.history import get_latest_summary, load_all_history
from agent.runner import EcommerceOpsAgent

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_run(args):
    agent = EcommerceOpsAgent(max_retries=args.retries)
    result = agent.run(data_date=args.date)

    print("\n" + "=" * 50)
    print("✅ 电商运营数字员工执行成功！")
    print("=" * 50)
    print(f"   数据日期: {result['data_date']}")
    print(f"   订单: {result['total_orders']} 笔")
    print(f"   销售额: ¥{result['total_amount']:,.2f}")
    print(f"   异常: {len(result['anomalies'])} 条")
    print(f"   耗时: {result['duration_sec']} 秒")
    print(f"   日报: {result['report_path']}")

    if result["anomalies"]:
        print("\n⚠️ 异常明细:")
        # 按类型统计
        from collections import Counter
        counts = Counter(a.type for a in result["anomalies"])
        for atype, count in counts.most_common():
            print(f"   - {atype}: {count} 条")

        # 显示严重异常（前5条）
        critical = [a for a in result["anomalies"] if a.level == "critical"][:5]
        if critical:
            print("\n🔴 严重异常:")
            for a in critical:
                print(f"   - [{a.type}] {a.reference_id}: {a.detail}")

    if result.get("anomaly_report_path"):
        print(f"\n   异常报告: {result['anomaly_report_path']}")


def cmd_schedule(args):
    logger.info("启动定时调度，每天 %02d:%02d 执行", config.SCHEDULE_HOUR, config.SCHEDULE_MINUTE)
    agent = EcommerceOpsAgent(max_retries=args.retries)

    while True:
        now = datetime.now()
        target = now.replace(hour=config.SCHEDULE_HOUR, minute=config.SCHEDULE_MINUTE, second=0, microsecond=0)
        if target <= now:
            # 已过今天的时间点，明天执行
            target = target + timedelta(days=1)
        wait_sec = (target - now).total_seconds()
        logger.info("距离下次执行还有 %.1f 小时", wait_sec / 3600)
        time.sleep(wait_sec)
        try:
            agent.run()
        except Exception as e:  # noqa: BLE001
            logger.error("本次调度执行失败: %s", e)


def cmd_history(args):
    records = load_all_history(limit=args.limit)
    if not records:
        print("暂无历史记录")
        return
    print(f"共 {len(records)} 条历史记录：\n")
    for r in records:
        status = "✅" if r.get("status") == "success" else "❌"
        print(f"{status} {r.get('data_date')} {r.get('timestamp')} | "
              f"订单 {r.get('total_orders', '-')} | 销售额 ¥{r.get('total_amount', '-')} | "
              f"异常 {r.get('anomaly_count', '-')} | 尝试 {r.get('attempts', 1)} 次")
    latest = get_latest_summary()
    if latest:
        print(f"\n最近一次: {latest}")


def cmd_audit(args):
    audit = AuditLog()
    entries = audit.get_recent(limit=args.limit)
    if not entries:
        print("暂无审计记录")
        return
    print(f"最近 {len(entries)} 条审计记录：\n")
    for e in entries:
        status_icon = "✅" if e["status"] == "success" else ("❌" if e["status"] == "failed" else "🔄")
        print(f"{status_icon} [{e['timestamp']}] {e['action']} ({e['task_type']}) - {e['status']}")
        if e.get("detail"):
            print(f"     └─ {e['detail']}")


def cmd_init_data(args):
    print("正在生成示例数据...")
    from generate_sample_data import main as gen_data
    gen_data()


def main():
    parser = argparse.ArgumentParser(description="电商运营数字员工")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="立即执行一次")
    p_run.add_argument("--date", help="数据日期 YYYY-MM-DD")
    p_run.add_argument("--retries", type=int, default=config.MAX_RETRIES, help="最大重试次数")
    p_run.set_defaults(func=cmd_run)

    p_sched = sub.add_parser("schedule", help="定时执行")
    p_sched.add_argument("--retries", type=int, default=config.MAX_RETRIES)
    p_sched.set_defaults(func=cmd_schedule)

    p_hist = sub.add_parser("history", help="查看历史记录")
    p_hist.add_argument("--limit", type=int, default=20, help="显示条数")
    p_hist.set_defaults(func=cmd_history)

    p_audit = sub.add_parser("audit", help="查看审计日志")
    p_audit.add_argument("--limit", type=int, default=20, help="显示条数")
    p_audit.set_defaults(func=cmd_audit)

    p_init = sub.add_parser("init-data", help="生成示例数据")
    p_init.set_defaults(func=cmd_init_data)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
