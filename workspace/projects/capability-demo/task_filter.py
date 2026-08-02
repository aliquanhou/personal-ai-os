#!/usr/bin/env python3
"""
AI 数字员工任务筛选器
验证：一个"具体、可量化、强规则"的任务是否适合做成数字员工。

对应老板的数字员工平台三大筛选标准：
1. 高重复 + 强规则（有固定SOP，不需创造判断）
2. 可量化 + ROI 一眼算清（处理量/工时/错误率）
3. 低信任成本 + 可人工兜底（出错代价低，能一键接管）
"""

import json
import sys


def score_task(task: dict) -> dict:
    """对单个任务打分，返回总分和各维度得分。"""
    # 三个维度，每维 0-1 分，权重相等
    scores = {}

    # 维度1: 高重复 + 强规则
    repeat = task.get("repeat_freq", 0)      # 0-1 重复频率
    rule_based = task.get("rule_based", 0)   # 0-1 规则化程度
    scores["repeat_rule"] = round((repeat + rule_based) / 2, 2)

    # 维度2: 可量化 + ROI 清晰
    quantifiable = task.get("quantifiable", 0)  # 0-1 可量化程度
    roi_clear = task.get("roi_clear", 0)        # 0-1 ROI清晰程度
    scores["quant_roi"] = round((quantifiable + roi_clear) / 2, 2)

    # 维度3: 低信任成本 + 可人工兜底
    low_trust_cost = task.get("low_trust_cost", 0)  # 0-1 出错代价低
    human_fallback = task.get("human_fallback", 0)  # 0-1 可人工接管
    scores["trust_fallback"] = round((low_trust_cost + human_fallback) / 2, 2)

    # 总分 (0-3)
    total = round(sum(scores.values()), 2)

    # 判定
    if total >= 2.4:
        verdict = "✅ 非常适合 → AI数字员工"
    elif total >= 1.8:
        verdict = "⚠️ 边缘任务 → 建议人工为主，AI辅助"
    else:
        verdict = "❌ 不合适 → 保留人工"

    return {"scores": scores, "total": total, "verdict": verdict}


def main():
    tasks = [
        {
            "name": "财务票据录入",
            "repeat_freq": 0.95, "rule_based": 0.9,
            "quantifiable": 0.95, "roi_clear": 0.9,
            "low_trust_cost": 0.8, "human_fallback": 0.9,
        },
        {
            "name": "销售成交",
            "repeat_freq": 0.5, "rule_based": 0.3,
            "quantifiable": 0.6, "roi_clear": 0.7,
            "low_trust_cost": 0.2, "human_fallback": 0.3,
        },
        {
            "name": "库存对账",
            "repeat_freq": 0.9, "rule_based": 0.85,
            "quantifiable": 0.9, "roi_clear": 0.8,
            "low_trust_cost": 0.7, "human_fallback": 0.85,
        },
        {
            "name": "复杂客服投诉处理",
            "repeat_freq": 0.6, "rule_based": 0.4,
            "quantifiable": 0.5, "roi_clear": 0.5,
            "low_trust_cost": 0.3, "human_fallback": 0.4,
        },
    ]

    print("=" * 60)
    print("AI 数字员工任务筛选器 — 能力验证")
    print("=" * 60)
    results = []
    for t in tasks:
        r = score_task(t)
        results.append((t["name"], r))
        print(f"\n任务: {t['name']}")
        print(f"  维度得分: 重复规则={r['scores']['repeat_rule']} "
              f"量化ROI={r['scores']['quant_roi']} "
              f"信任兜底={r['scores']['trust_fallback']}")
        print(f"  总分: {r['total']}/3  →  {r['verdict']}")

    print("\n" + "=" * 60)
    print("结论：符合老板'任务工厂'定位——高重复+强规则+可兜底的任务才值得做数字员工")
    print("=" * 60)

    # 输出 JSON 供其他程序消费
    if "--json" in sys.argv:
        print("\nJSON 输出:")
        print(json.dumps(
            [{"name": n, **r} for n, r in results],
            ensure_ascii=False, indent=2
        ))


if __name__ == "__main__":
    main()
