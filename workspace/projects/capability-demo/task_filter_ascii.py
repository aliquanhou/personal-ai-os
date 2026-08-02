#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Digital Employee Task Filter (ASCII version for console display test)
Scores a task against the 3 criteria for "digital employee" suitability.
"""
import json

def score_task(t):
    s = {}
    s["repeat_rule"] = round((t["repeat_freq"] + t["rule_based"]) / 2, 2)
    s["quant_roi"]   = round((t["quantifiable"] + t["roi_clear"]) / 2, 2)
    s["trust_fallback"] = round((t["low_trust_cost"] + t["human_fallback"]) / 2, 2)
    total = round(sum(s.values()), 2)
    if total >= 2.4:   v = "PERFECT -> digital employee"
    elif total >= 1.8: v = "EDGE -> human-first, AI assist"
    else:              v = "NO -> keep human"
    return {"scores": s, "total": total, "verdict": v}

TASKS = [
    {"name": "invoice-entry", "repeat_freq":.95,"rule_based":.9,"quantifiable":.95,"roi_clear":.9,"low_trust_cost":.8,"human_fallback":.9},
    {"name": "sales-close",   "repeat_freq":.5,"rule_based":.3,"quantifiable":.6,"roi_clear":.7,"low_trust_cost":.2,"human_fallback":.3},
    {"name": "stock-reconcile","repeat_freq":.9,"rule_based":.85,"quantifiable":.9,"roi_clear":.8,"low_trust_cost":.7,"human_fallback":.85},
    {"name": "complex-support","repeat_freq":.6,"rule_based":.4,"quantifiable":.5,"roi_clear":.5,"low_trust_cost":.3,"human_fallback":.4},
]

for t in TASKS:
    r = score_task(t)
    print(f"{t['name']:<18} total={r['total']}  {r['verdict']}")

print("\nJSON:")
print(json.dumps([{"name": t["name"], **score_task(t)} for t in TASKS], indent=2))
