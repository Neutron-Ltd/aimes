"""Excel export — flatten orchestrator result to spreadsheet."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd


def export_to_excel(result: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    rows: list[dict[str, Any]] = []

    def _flatten(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                _flatten(v, f"{prefix}{k}.")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, dict):
                    row = {f"{prefix[:-1]}[{i}].{kk}": vv for kk, vv in item.items()}
                    rows.append(row)
                else:
                    rows.append({prefix[:-1]: str(item)})
        else:
            rows.append({prefix[:-1]: obj})

    _flatten(result)
    if not rows:
        rows = [{"message": "No data"}]

    df = pd.json_normalize(rows) if rows else pd.DataFrame([{"message": "empty"}])
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    buffer.seek(0)
    return buffer.getvalue()
