"""PDF export — tabular summary via reportlab."""

from __future__ import annotations

import io
import json
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def export_to_pdf(result: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "NEUTRON MES Report")
    y -= 30
    c.setFont("Helvetica", 9)

    text = json.dumps(result, indent=2, default=str)
    for line in text.splitlines():
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)
        c.drawString(50, y, line[:110])
        y -= 12

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
