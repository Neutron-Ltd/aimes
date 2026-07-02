#!/usr/bin/env python3
"""Run question-1.1 scenarios through POST /api/v1/query (Bailian + MCP)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

QUERIES: list[tuple[str, str, bool]] = [
    (
        "S1",
        "Show me the equipment output for each product corresponding to the 防盗器贴片六线 (FDQ-SMT-6) line over the week ending on 2026-06-21.",
        True,
    ),
    (
        "S2",
        "Record the equipment output for product 2101901300015 (YB130-FBXX-05-Y 蓝牙仪表（四个插针）/新增TLV协议送检/ 芯片协议 昂瑞薇  程序：空片 板子刷三防漆) on the 防盗器贴片六线 line for 2026-06-21.",
        True,
    ),
    (
        "S3",
        "Compile statistics on the average daily production output per product for the LED贴片车间二线 (LED-SMT-2) line over the high-volume week of 2026-06-11 to 2026-06-17.",
        True,
    ),
    (
        "S4",
        "Record the average production rates for the products associated with the 防盗器贴片三线 line on 2026-06-20, including the specific performance of machine 贴片机三线 (BB-SMT-029).",
        True,
    ),
    (
        "S5",
        "Calculate the total production of product 2101200000247 (TL-WL-14K-04-A台铃14孔物联中控双频多模坐垫锁五金天线 程序:空片) associated with the 鸿志贴片五线 (HZ-SMT-5) line over the week leading up to 2026-06-21, including both labor manual reports (t_wip_detail) and equipment output (t_smt_program_consumption_record).",
        False,
    ),
    (
        "S6",
        "Record the total production (net quantity) of product 2101200760385 (S76-6+4-TLLARW-C(台铃-6+4-蓝牙-昂瑞微-缩小边框) 程序：空片) associated with the 防盗器贴片一线 (FDQ-SMT-1) line for the day of 2026-06-21.",
        False,
    ),
    (
        "S7",
        "Calculate the volatility (standard deviation) of equipment output for product 2101209060045 (BB906-TL-LY-20K-OLW...) over the high-volume week of 2026-06-11 to 2026-06-17. Identify which specific day had the most unstable production.",
        True,
    ),
    (
        "S8",
        "Identify the hourly time periods on 2026-06-15 when the output of equipment on the 防盗器贴片一线 line fell below 80% of its 'hourly standard production rate' (calculated from the 86-second standard time for item 2101200000217) and list the specific values.",
        True,
    ),
    (
        "S9",
        "Compare the output of equipment during the current shift period today (2026-06-21) with the same time period yesterday (2026-06-20) on the 防盗器贴片六线 line to calculate the growth or decline rate.",
        True,
    ),
    (
        "S10",
        "Calculate the daily equipment output rate vs target (actual output / target output) for product 2101200000242 (TL-WL-14K-01-A3台铃14孔物联中控...) corresponding to the 鸿志贴片七线 (HZ-SMT-7) line over the week ending 2026-06-21.",
        False,
    ),
    (
        "S11",
        "What is the highest hourly output peak of the equipment for the 防盗器贴片三线 production line when operating at full capacity?",
        True,
    ),
    (
        "S12",
        "Analyze the trend in equipment output for the LED贴片车间三线 (LED-SMT-3) product line over the past week (increase/decrease/stability) from 2026-06-15 to 2026-06-21 and predict the estimated total output for tomorrow, 2026-06-22.",
        True,
    ),
    (
        "S13",
        "Analyze the distribution of the 'peak production periods' for the 防盗器贴片六线 line over the course of the week ending 2026-06-21 (occurring at a frequency greater than 30% of the average output). Determine whether there are any consistent periods of production bottlenecks.",
        True,
    ),
]

API_URL = "http://localhost/api/v1/query"


def _numeric_values(obj: Any) -> list[float]:
    out: list[float] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and v != 0:
                out.append(float(v))
            elif isinstance(v, (dict, list)):
                out.extend(_numeric_values(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_numeric_values(item))
    return out


def has_meaningful_mcp_data(resp: dict[str, Any]) -> tuple[bool, str]:
    if resp.get("intent", {}).get("parse_error"):
        return False, f"Intent parse error: {resp['intent']['parse_error']}"

    intent = resp.get("intent", {}).get("intent")
    if intent == "unknown":
        return False, "Bailian classified intent as UNKNOWN — no MCP tool ran"

    tool = resp.get("tool_name")
    if not tool:
        msg = (resp.get("message") or "")[:200]
        return False, f"No MCP tool invoked. Message: {msg}"

    result = resp.get("result")
    if result is None:
        msg = (resp.get("message") or "")[:200]
        return False, f"MCP tool '{tool}' returned no result. Message: {msg}"

    # Yield aggregation
    if "value" in result:
        value = float(result.get("value") or 0)
        breakdown = result.get("breakdown") or []
        if value > 0:
            return True, f"value={value}"
        if breakdown and any(float(b.get("value") or 0) > 0 for b in breakdown):
            return True, f"breakdown rows={len(breakdown)}"
        if breakdown and any(float(b.get("good_qty") or 0) > 0 for b in breakdown):
            return True, f"breakdown good_qty rows={len(breakdown)}"

    # Anomalies nested result
    nested = result.get("result")
    if isinstance(nested, dict):
        if float(nested.get("peak_value") or 0) > 0:
            return True, f"peak_value={nested['peak_value']}"
        if int(nested.get("bucket_count") or 0) > 0 and float(nested.get("mean") or 0) > 0:
            return True, f"volatility buckets={nested['bucket_count']}"
        if int(nested.get("below_standard_count") or 0) > 0:
            return True, f"below_standard_count={nested['below_standard_count']}"
        flagged = nested.get("flagged_buckets") or []
        if flagged:
            return True, f"flagged_buckets={len(flagged)}"

    # Period comparison
    p1 = float(result.get("period_1_total") or 0)
    p2 = float(result.get("period_2_total") or 0)
    if p1 > 0 or p2 > 0:
        return True, f"period_1_total={p1}, period_2_total={p2}"

    # Device rate / product yield totals
    for key in ("total", "total_qty", "total_good_qty", "avg_rate"):
        if float(result.get(key) or 0) > 0:
            return True, f"{key}={result[key]}"

    breakdown = result.get("breakdown") or result.get("devices") or result.get("daily_breakdown") or []
    if breakdown and _numeric_values(breakdown):
        return True, f"breakdown/list rows={len(breakdown)}"

    nums = _numeric_values(result)
    if nums:
        return True, f"numeric fields found: {nums[:3]}"

    return False, f"MCP tool '{tool}' ran but returned empty/zero payload: {json.dumps(result)[:300]}"


def post_query(query: str) -> dict[str, Any]:
    body = json.dumps(
        {"query": query, "enrich_response": True, "locale": "en-US"}
    ).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    results = []
    for sid, query, db_available in QUERIES:
        print(f"Running {sid}...", flush=True)
        try:
            resp = post_query(query)
            mcp_ok, detail = has_meaningful_mcp_data(resp)
            results.append(
                {
                    "scenario": sid,
                    "db_available": db_available,
                    "mcp_available": mcp_ok,
                    "detail": detail,
                    "tool_name": resp.get("tool_name"),
                    "intent": resp.get("intent", {}).get("intent"),
                    "result": resp.get("result"),
                    "message_preview": (resp.get("message") or "")[:400],
                }
            )
            print(f"  {sid}: MCP={'AVAILABLE' if mcp_ok else 'NOT_AVAILABLE'} — {detail}")
        except Exception as exc:
            results.append(
                {
                    "scenario": sid,
                    "db_available": db_available,
                    "mcp_available": False,
                    "detail": str(exc),
                    "error": True,
                }
            )
            print(f"  {sid}: ERROR — {exc}")

    out_path = "/tmp/mcp_question_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
