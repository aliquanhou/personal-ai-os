"""修复相对导入为绝对导入（临时脚本）。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

replacements = {
    "agent/audit.py":        {"from ..db import db": "from db import db"},
    "agent/runner.py":       {"from ..db import db, models": "from db import db, models",
                              "from . import audit, loader, registry, report, rules": "from agent import audit, loader, registry, report, rules"},
    "agent/registry.py":     {"from ..db import models": "from db import models",
                              "from .tasks import order_check, product_clean, stock_reconcile": "from agent.tasks import order_check, product_clean, stock_reconcile"},
    "db/db.py":              {"from . import models": "from db import models"},
    "agent/tasks/order_check.py":   {"from .. import rules": "from agent import rules"},
    "agent/tasks/product_clean.py": {"from .. import rules": "from agent import rules"},
    "agent/tasks/stock_reconcile.py": {"from .. import rules": "from agent import rules"},
}

for rel, mapping in replacements.items():
    path = os.path.join(BASE_DIR, rel)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for old, new in mapping.items():
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK {rel}")
