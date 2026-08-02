"""销售数据分析数字员工 - 主执行流程 + 失败自动重试"""
import logging
import time
from datetime import datetime

from . import analyzer, config, excel_reader, history, report

logger = logging.getLogger(__name__)


class SalesAnalystAgent:
    """销售数据分析数字员工

    功能：
    1. 读取 Excel 销售数据
    2. 分析销售排名
    3. 找出异常订单
    4. 生成日报
    5. 保存历史记录
    6. 失败自动重试
    """

    def __init__(self, max_retries: int = None, retry_backoff: int = None):
        self.max_retries = max_retries if max_retries is not None else config.MAX_RETRIES
        self.retry_backoff = retry_backoff if retry_backoff is not None else config.RETRY_BACKOFF_SEC

    def run(self, data_date: str = None) -> dict:
        """执行完整流程，带失败自动重试"""
        data_date = data_date or datetime.now().strftime("%Y-%m-%d")
        attempt = 0
        last_error = None

        while attempt <= self.max_retries:
            try:
                if attempt > 0:
                    logger.info("第 %d 次重试...", attempt)
                result = self._run_once(data_date)
                result["attempts"] = attempt + 1
                return result
            except Exception as e:  # noqa: BLE001
                attempt += 1
                last_error = e
                logger.error("执行失败（第 %d/%d 次）: %s", attempt, self.max_retries + 1, e)
                if attempt <= self.max_retries:
                    wait = self.retry_backoff * (2 ** (attempt - 1))
                    logger.info("等待 %d 秒后重试...", wait)
                    time.sleep(wait)

        # 所有重试都失败
        failure_record = {
            "status": "failed",
            "data_date": data_date,
            "error": str(last_error),
            "attempts": self.max_retries + 1,
            "timestamp": datetime.now().isoformat(),
        }
        history.save_history(failure_record)
        raise RuntimeError(f"销售分析任务失败，已重试 {self.max_retries} 次: {last_error}")

    def _run_once(self, data_date: str) -> dict:
        """单次执行（无重试）"""
        # 1. 读取 Excel
        files = excel_reader.find_input_files()
        if not files:
            raise FileNotFoundError(
                f"未找到销售数据文件（匹配 {config.INPUT_PATTERN}），请放入目录: {config.INPUT_DIR}"
            )
        logger.info("找到 %d 个数据文件: %s", len(files), [f.name for f in files])

        frames = [excel_reader.read_excel(f) for f in files]
        df = _concat_frames(frames)

        missing = excel_reader.validate_columns(df)
        if missing:
            raise ValueError(f"数据缺少必需列: {missing}")

        # 2. 分析（排名 + 异常检测）
        result = analyzer.analyze(df)

        # 3. 生成日报
        report_text = report.generate_report(result, data_date)
        report_path = report.save_report(report_text, data_date)

        # 4. 保存历史记录
        history_record = {
            "status": "success",
            "data_date": data_date,
            "timestamp": datetime.now().isoformat(),
            "total_orders": result["total_orders"],
            "total_amount": result["total_amount"],
            "total_qty": result["total_qty"],
            "anomaly_count": len(result["anomalies"]),
            "report_path": report_path,
            "anomalies": result["anomalies"],
            "top_products": result["product_ranking"][:5],
            "top_customers": result["customer_ranking"][:5],
        }
        history.save_history(history_record)

        result["report_path"] = report_path
        logger.info(
            "✅ 任务完成: 订单 %d 笔, 销售额 ¥%.2f, 异常 %d 条, 日报: %s",
            result["total_orders"], result["total_amount"],
            len(result["anomalies"]), report_path,
        )
        return result


def _concat_frames(frames: list) -> "pd.DataFrame":
    """合并多个 DataFrame"""
    import pandas as pd
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, ignore_index=True)
