"""生成模拟销售数据 Excel 用于验证"""
import random
from datetime import datetime, timedelta

import pandas as pd

from agent import config

random.seed(42)

CUSTOMERS = ["阿里巴巴", "腾讯科技", "字节跳动", "华为", "小米", "美团", "京东", "网易", "百度", "拼多多"]
PRODUCTS = ["智能音箱", "无线耳机", "智能手表", "蓝牙键盘", "显示器", "机械键盘", "鼠标", "摄像头", "路由器", "充电宝"]


def gen_sales_data(n=200, date="2026-08-01") -> pd.DataFrame:
    rows = []
    for i in range(n):
        qty = random.randint(1, 20)
        price = random.choice([99, 199, 299, 499, 799, 1299, 1999])
        amount = qty * price
        # 注入几个异常
        if i % 50 == 0:      # 超高价异常
            amount = 999999
        if i % 70 == 0:      # 数量异常
            qty = -5
        rows.append({
            config.COL_ORDER_ID: f"ORD-{date.replace('-','')}-{1000+i}",
            config.COL_DATE: date,
            config.COL_CUSTOMER: random.choice(CUSTOMERS),
            config.COL_PRODUCT: random.choice(PRODUCTS),
            config.COL_QTY: qty,
            config.COL_AMOUNT: amount,
            config.COL_STATUS: "已支付",
        })
    # 注入一条重复订单
    rows.append({
        config.COL_ORDER_ID: "ORD-DUP-001",
        config.COL_DATE: date,
        config.COL_CUSTOMER: "阿里巴巴",
        config.COL_PRODUCT: "智能音箱",
        config.COL_QTY: 10,
        config.COL_AMOUNT: 1990,
        config.COL_STATUS: "已支付",
    })
    rows.append({
        config.COL_ORDER_ID: "ORD-DUP-002",
        config.COL_DATE: date,
        config.COL_CUSTOMER: "阿里巴巴",
        config.COL_PRODUCT: "智能音箱",
        config.COL_QTY: 10,
        config.COL_AMOUNT: 1990,
        config.COL_STATUS: "已支付",
    })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    df = gen_sales_data(200, date)
    out = config.INPUT_DIR / f"sales_{date}.xlsx"
    df.to_excel(out, index=False, engine="openpyxl")
    print(f"已生成模拟数据: {out} ({len(df)} 行)")
