"""诊断 setup 流程，结果写入日志文件。"""
import sys, os, traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE_DIR, "_diag.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# 清空日志
with open(LOG, "w", encoding="utf-8") as f:
    f.write("")

sys.path.insert(0, BASE_DIR)
try:
    from db import db, models
    from agent import runner
    log("import ok")

    path = db.init_db()
    log("db init: " + path)

    from generate_sample_data import main as gen
    gen.__globals__['print'] = lambda *a, **k: log(" ".join(str(x) for x in a))
    gen()
    log("data gen ok")

    agent = runner.EcommerceOpsAgent()
    tid1 = agent.create_task("每日订单核对", models.TASK_TYPE_ORDER_CHECK,
                             {}, "daily:09:00", review_required=1)
    tid2 = agent.create_task("库存对账", models.TASK_TYPE_STOCK_RECONCILE,
                             {"tolerance": 2}, "daily:22:00", review_required=1)
    tid3 = agent.create_task("商品资料清洗", models.TASK_TYPE_PRODUCT_CLEAN,
                             {}, "daily:23:00", review_required=0)
    log("tasks: %s %s %s" % (tid1, tid2, tid3))
    log("SETUP OK")
except Exception:
    tb = traceback.format_exc()
    log(tb)
