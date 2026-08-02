"""pytest 配置：确保项目根目录可导入。"""

import os
import sys

# 将项目根目录加入 sys.path，使 agent/db 可作为顶层包导入
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
