"""日报生成：将执行结果输出为文本报告。"""

import os
from datetime import datetime


def generate_report(task_name: str, stats: dict, anomalies: list,
                    data_date: str, output_dir: str) -> str:
    """生成日报文本文件，返回文件路径。"""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{task_name}_{data_date}_{ts}.txt")

    lines = [
        "=" * 50,
        f"电商运营数字员工 - 日报",
        "=" * 50,
        f"任务: {task_name}",
        f"数据日期: {data_date}",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-" * 50,
    ]

    # 统计信息
    for k, v in stats.items():
        lines.append(f"  {k}: {v}")

    # 异常明细
    if anomalies:
        lines.append("-" * 50)
        lines.append(f"异常明细 ({len(anomalies)} 条):")
        for a in anomalies[:20]:
            lines.append(f"  [{a.level}] {a.type} | {a.reference_id}: {a.detail}")
        if len(anomalies) > 20:
            lines.append(f"  ... 共 {len(anomalies)} 条，仅显示前 20 条")
    else:
        lines.append("-" * 50)
        lines.append("✅ 无异常")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path
