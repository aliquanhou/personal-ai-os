"""诊断 setup 流程。"""
import sys, os, traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from db import db, models
    from agent import runner

    print("import ok")
    path = db.init_db()
    print("db init:", path)

    from generate_sample_data import main as gen
    gen()
    print("data gen ok")

    agent = runner.EcommerceOpsAgent()
    tid1 = agent.create_task("每日订单核对", models.TASK_TYPE_ORDER_CHECK,
                             {}, "daily:09:00", review_required=1)
    tid2 = agent.create_task("库存对账", models.TASK_TYPE_STOCK_RECONCILE,
                             {"tolerance": 2}, "daily:22:00", review_required=1)
    tid3 = agent.create_task("商品资料清洗", models.TASK_TYPE_PRODUCT_CLEAN,
                             {}, "daily:23:00", review_required=0)
    print("tasks:", tid1, tid2, tid3)
    print("SETUP OK")
except Exception:
    traceback.print_exc()
