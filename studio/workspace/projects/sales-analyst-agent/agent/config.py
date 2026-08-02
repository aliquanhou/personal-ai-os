"""销售数据分析数字员工 - 配置模块"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"      # 待分析的Excel文件
HISTORY_DIR = DATA_DIR / "history"  # 历史记录（JSON）
REPORTS_DIR = DATA_DIR / "reports"  # 生成的日报

# 确保目录存在
for _d in (INPUT_DIR, HISTORY_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# 输入Excel文件（支持 glob 匹配多个文件，如 sales_2026*.xlsx）
INPUT_PATTERN = "sales*.xlsx"

# ── 异常检测阈值 ──
# 订单金额异常：偏离订单均值超过 N 倍标准差
AMOUNT_STD_MULT = 3.0
# 单笔金额异常下限/上限（绝对值，元）
AMOUNT_MIN = 0
AMOUNT_MAX = 1_000_000
# 数量异常：非正数或超过 MAX_QTY
QTY_MAX = 10_000
# 重复订单：相同客户+金额+时间窗口内（分钟）
DUP_TIME_WINDOW_MIN = 30

# ── 调度 ──
# 每日执行时间（24小时制）
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0

# ── 重试 ──
MAX_RETRIES = 3          # 最大重试次数（不含首次）
RETRY_BACKOFF_SEC = 5    # 首次重试等待（秒），之后指数增长

# 列名配置（可适配不同Excel模板）
COL_ORDER_ID = "订单号"
COL_DATE = "日期"
COL_CUSTOMER = "客户"
COL_PRODUCT = "商品"
COL_QTY = "数量"
COL_AMOUNT = "金额"
COL_STATUS = "状态"
