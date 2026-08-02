"""运行所有启用任务并输出结果到日志。"""
import sys, os, traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE_DIR, "_run.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

with open(LOG, "w", encoding="utf-8") as f:
    f.write("")

sys.path.insert(0, BASE_DIR)
try:
    from agent import runner
    agent = runner.EcommerceOpsAgent()
    tasks = agent.list_tasks()
    for t in tasks:
        if t["enabled"]:
            log("=== 执行任务: %s (%s) ===" % (t["name"], t["task_type"]))
            result = agent.run_task(t["id"])
            log("  状态: %s | 数据日期: %s" % (result["status"], result["data_date"]))
            log("  统计: %s" % result["stats"])
            log("  异常: %d 条 | 耗时: %ss" % (len(result["anomalies"]), result["duration_sec"]))
            log("  日报: %s" % result["report_path"])
            for a in result["anomalies"][:5]:
                log("    [%s] %s | %s: %s" % (a.level, a.type, a.reference_id, a.detail))
    log("RUN-ALL OK")
except Exception:
    log(traceback.format_exc())
