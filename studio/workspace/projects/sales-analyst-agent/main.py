"""销售数据分析数字员工 - 入口

用法：
    python main.py run                # 立即执行一次
    python main.py run --date 2026-01-01   # 指定数据日期
    python main.py schedule           # 按配置定时执行（默认每天 09:00）
    python main.py history            # 查看历史记录
"""
import argparse
import logging
import time
from datetime import datetime

from agent import config
from agent.history import get_latest_summary, load_all_history
from agent.runner import SalesAnalystAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_run(args):
    agent = SalesAnalystAgent(max_retries=args.retries)
    result = agent.run(data_date=args.date)
    print(f"\n✅ 执行成功！")
    print(f"   订单: {result['total_orders']} 笔")
    print(f"   销售额: ¥{result['total_amount']:,.2f}")
    print(f"   异常: {len(result['anomalies'])} 条")
    print(f"   日报: {result['report_path']}")
    if result["anomalies"]:
        print("\n⚠️ 异常订单:")
        for a in result["anomalies"]:
            print(f"   - [{a['type']}] {a['order_id']}: {a['detail']}")


def cmd_schedule(args):
    logger.info("启动定时调度，每天 %02d:%02d 执行", config.SCHEDULE_HOUR, config.SCHEDULE_MINUTE)
    agent = SalesAnalystAgent(max_retries=args.retries)
    while True:
        now = datetime.now()
        target = now.replace(hour=config.SCHEDULE_HOUR, minute=config.SCHEDULE_MINUTE, second=0, microsecond=0)
        if target <= now:
            # 已过今天的时间点，明天执行
            from datetime import timedelta
            target = target + timedelta(days=1)
        wait_sec = (target - now).total_seconds()
        logger.info("距离下次执行还有 %.1f 小时", wait_sec / 3600)
        time.sleep(wait_sec)
        try:
            agent.run()
        except Exception as e:  # noqa: BLE001
            logger.error("本次调度执行失败: %s", e)


def cmd_history(args):
    records = load_all_history()
    if not records:
        print("暂无历史记录")
        return
    print(f"共 {len(records)} 条历史记录：\n")
    for r in records:
        status = "✅" if r.get("status") == "success" else "❌"
        print(f"{status} {r.get('data_date')} {r.get('timestamp')} | "
              f"订单 {r.get('total_orders', '-')} | 销售额 {r.get('total_amount', '-')} | "
              f"异常 {r.get('anomaly_count', '-')} | 尝试 {r.get('attempts', 1)} 次")
    latest = get_latest_summary()
    if latest:
        print(f"\n最近一次: {latest}")


def main():
    parser = argparse.ArgumentParser(description="销售数据分析数字员工")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="立即执行一次")
    p_run.add_argument("--date", help="数据日期 YYYY-MM-DD")
    p_run.add_argument("--retries", type=int, default=config.MAX_RETRIES, help="最大重试次数")
    p_run.set_defaults(func=cmd_run)

    p_sched = sub.add_parser("schedule", help="定时执行")
    p_sched.add_argument("--retries", type=int, default=config.MAX_RETRIES)
    p_sched.set_defaults(func=cmd_schedule)

    p_hist = sub.add_parser("history", help="查看历史记录")
    p_hist.set_defaults(func=cmd_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
