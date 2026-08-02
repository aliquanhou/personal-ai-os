"""电商运营数字员工 - 配置中心"""

from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
ORDERS_FILE = DATA_DIR / "sample_orders.csv"
INVENTORY_FILE = DATA_DIR / "sample_inventory.csv"
PRODUCTS_FILE = DATA_DIR / "sample_products.csv"

# 输出目录
OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = OUTPUT_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 数据库
DB_PATH = BASE_DIR / "data" / "ops_agent.db"

# 调度配置
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0

# 规则配置
MAX_RETRIES = 3
INVENTORY_TOLERANCE = 0  # 库存允许差异（绝对数量）
PRICE_MIN = 0.01  # 商品最低售价
COST_MIN = 0.0  # 商品最低成本

# 订单状态
ORDER_STATUS_VALID = {"pending", "paid", "shipped", "completed", "cancelled"}

# 平台列表
PLATFORMS = {"taobao", "jd", "pdd", "douyin", "wechat"}

# 商品状态
PRODUCT_STATUS_VALID = {"on_sale", "off_sale", "pending"}

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
