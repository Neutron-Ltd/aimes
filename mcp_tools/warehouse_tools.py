"""Warehouse module MCP tools — inventory, FIFO, obsolete, traceability."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text

from core.db import get_session
from mcp_tools.base import BaseMCPTool
from models.intents.warehouse import (
    InboundOutboundParams,
    InboundOutboundResult,
    InventoryStatusParams,
    InventoryStatusResult,
    ObsoleteProfileParams,
    ObsoleteProfileResult,
    TraceForwardParams,
    TraceForwardResult,
    TraceReverseParams,
    TraceReverseResult,
)
from models.schemas import MCPContext


class GetInventoryStatusTool(BaseMCPTool[InventoryStatusParams, InventoryStatusResult]):
    name = "get_inventory_status"
    description = "Low stock and expiring inventory from t_wms_stock_info."

    async def execute(
        self, params: InventoryStatusParams, context: MCPContext
    ) -> InventoryStatusResult:
        session = await get_session()
        try:
            filters = ["s.data_auth = :workshop_id"]
            bind: dict[str, Any] = {"workshop_id": context.workshop_id}
            if params.wh_code:
                filters.append("s.wh_code = :wh_code")
                bind["wh_code"] = params.wh_code
            if params.item_code:
                filters.append("s.item_code = :item_code")
                bind["item_code"] = params.item_code

            sql = text(
                f"""
                SELECT s.item_code, s.item_qty, s.wh_code, s.invalid_date,
                       ci.min_stock
                FROM n2admin.t_wms_stock_info s
                LEFT JOIN n2admin.t_co_item ci ON s.item_code = ci.item_code
                WHERE {" AND ".join(filters)}
                """
            )
            result = await session.execute(sql, bind)
            rows = [dict(r) for r in result.mappings().all()]
        finally:
            await session.close()

        low_stock = []
        expiring = []
        soon = datetime.now() + timedelta(days=30)
        for r in rows:
            qty = float(r.get("item_qty") or 0)
            min_stock = float(r.get("min_stock") or 0)
            if min_stock and qty < min_stock:
                low_stock.append(
                    {
                        "item_code": r.get("item_code"),
                        "qty": qty,
                        "min_stock": min_stock,
                        "wh_code": r.get("wh_code"),
                    }
                )
            invalid = r.get("invalid_date")
            if invalid and invalid <= soon:
                expiring.append(
                    {
                        "item_code": r.get("item_code"),
                        "invalid_date": str(invalid),
                        "wh_code": r.get("wh_code"),
                    }
                )

        return InventoryStatusResult(
            workshop_id=context.workshop_id,
            low_stock=low_stock,
            expiring=expiring,
        )


class GuideInboundOutboundTool(BaseMCPTool[InboundOutboundParams, InboundOutboundResult]):
    name = "guide_inbound_outbound"
    description = "Bay recommendation and FIFO lot ordering."

    async def execute(
        self, params: InboundOutboundParams, context: MCPContext
    ) -> InboundOutboundResult:
        session = await get_session()
        try:
            area_sql = text(
                """
                SELECT storage_code, district_code
                FROM n2admin.t_wms_area
                WHERE wh_code = :wh_code AND data_auth = :workshop_id
                LIMIT 1
                """
            )
            stock_sql = text(
                """
                SELECT item_lot, item_qty, instock_time
                FROM n2admin.t_wms_stock_info
                WHERE wh_code = :wh_code AND item_code = :item_code
                  AND data_auth = :workshop_id AND item_qty > 0
                ORDER BY instock_time ASC
                """
            )
            bind = {
                "wh_code": params.wh_code,
                "item_code": params.item_code,
                "workshop_id": context.workshop_id,
            }
            area = (await session.execute(area_sql, bind)).mappings().first()
            lots = [dict(r) for r in (await session.execute(stock_sql, bind)).mappings().all()]
        finally:
            await session.close()

        recommended = None
        if area:
            recommended = area.get("storage_code") or area.get("district_code")

        fifo_lots = sorted(
            lots,
            key=lambda x: x.get("instock_time") or datetime.min,
        )
        return InboundOutboundResult(
            workshop_id=context.workshop_id,
            recommended_bay=recommended,
            fifo_lots=[
                {
                    "item_lot": l.get("item_lot"),
                    "qty": float(l.get("item_qty") or 0),
                    "instock_time": str(l.get("instock_time")),
                }
                for l in fifo_lots
            ],
        )


class ProfileObsoleteInventoryTool(BaseMCPTool[ObsoleteProfileParams, ObsoleteProfileResult]):
    name = "profile_obsolete_inventory"
    description = "Stagnant stock profile using dull_cycle from t_co_item."

    async def execute(
        self, params: ObsoleteProfileParams, context: MCPContext
    ) -> ObsoleteProfileResult:
        session = await get_session()
        try:
            filters = ["s.data_auth = :workshop_id", "s.item_qty > 0"]
            bind: dict[str, Any] = {"workshop_id": context.workshop_id}
            if params.wh_code:
                filters.append("s.wh_code = :wh_code")
                bind["wh_code"] = params.wh_code

            sql = text(
                f"""
                SELECT s.item_code, s.item_qty, s.wh_code, s.instock_time,
                       COALESCE(ci.dull_cycle, :default_dull) AS dull_cycle
                FROM n2admin.t_wms_stock_info s
                LEFT JOIN n2admin.t_co_item ci ON s.item_code = ci.item_code
                WHERE {" AND ".join(filters)}
                """
            )
            bind["default_dull"] = params.dull_days_threshold
            result = await session.execute(sql, bind)
            rows = [dict(r) for r in result.mappings().all()]
        finally:
            await session.close()

        stagnant = []
        cutoff = datetime.now() - timedelta(days=params.dull_days_threshold)
        for r in rows:
            instock = r.get("instock_time")
            if instock and instock < cutoff:
                stagnant.append(
                    {
                        "item_code": r.get("item_code"),
                        "qty": float(r.get("item_qty") or 0),
                        "wh_code": r.get("wh_code"),
                        "instock_time": str(instock),
                        "dull_cycle_days": float(r.get("dull_cycle") or params.dull_days_threshold),
                    }
                )

        return ObsoleteProfileResult(workshop_id=context.workshop_id, stagnant_items=stagnant)


class TraceMaterialForwardTool(BaseMCPTool[TraceForwardParams, TraceForwardResult]):
    name = "trace_material_forward"
    description = "Forward trace: material lot → WIP → finished lot (2-hop)."""

    async def execute(
        self, params: TraceForwardParams, context: MCPContext
    ) -> TraceForwardResult:
        session = await get_session()
        try:
            # Hop 1: WMS mid item by material lot
            sql = text(
                """
                SELECT m.item_code, m.item_lot, m.item_sn
                FROM n2admin.t_wms_mid_item m
                WHERE m.item_lot = :material_batch
                  AND m.data_auth = :workshop_id
                LIMIT 20
                """
            )
            mid_rows = [
                dict(r)
                for r in (
                    await session.execute(
                        sql,
                        {
                            "material_batch": params.material_batch,
                            "workshop_id": context.workshop_id,
                        },
                    )
                ).mappings().all()
            ]

            # Hop 2: WIP detail by pro_lot / item linkage
            wip_sql = text(
                """
                SELECT wd.pro_lot, wd.model_code, wd.pro_qty
                FROM n2admin.t_wip_detail wd
                WHERE wd.data_auth = :workshop_id
                  AND wd.pro_lot IN (
                      SELECT DISTINCT item_lot FROM n2admin.t_wms_mid_item
                      WHERE item_lot = :material_batch AND data_auth = :workshop_id
                  )
                LIMIT 20
                """
            )
            wip_rows = [
                dict(r)
                for r in (
                    await session.execute(
                        wip_sql,
                        {
                            "material_batch": params.material_batch,
                            "workshop_id": context.workshop_id,
                        },
                    )
                ).mappings().all()
            ]
        finally:
            await session.close()

        chain = [{"hop": 1, "source": "t_wms_mid_item", "records": mid_rows}]
        if wip_rows:
            chain.append({"hop": 2, "source": "t_wip_detail", "records": wip_rows})

        return TraceForwardResult(workshop_id=context.workshop_id, chain=chain)


class TraceProductReverseTool(BaseMCPTool[TraceReverseParams, TraceReverseResult]):
    name = "trace_product_reverse"
    description = "Reverse trace: finished lot → item SN log → WMS mid item (2-hop)."""

    async def execute(
        self, params: TraceReverseParams, context: MCPContext
    ) -> TraceReverseResult:
        session = await get_session()
        try:
            wip_sql = text(
                """
                SELECT wd.pro_lot, wd.model_code, wd.pro_qty
                FROM n2admin.t_wip_detail wd
                WHERE wd.pro_lot = :finished_lot
                  AND wd.data_auth = :workshop_id
                LIMIT 10
                """
            )
            wip_rows = [
                dict(r)
                for r in (
                    await session.execute(
                        wip_sql,
                        {
                            "finished_lot": params.finished_lot,
                            "workshop_id": context.workshop_id,
                        },
                    )
                ).mappings().all()
            ]

            mid_sql = text(
                """
                SELECT m.item_code, m.item_lot, m.supplier_code
                FROM n2admin.t_wms_mid_item m
                WHERE m.data_auth = :workshop_id
                  AND m.item_lot IN (
                      SELECT pro_lot FROM n2admin.t_wip_detail
                      WHERE pro_lot = :finished_lot AND data_auth = :workshop_id
                  )
                LIMIT 20
                """
            )
            mid_rows = [
                dict(r)
                for r in (
                    await session.execute(
                        mid_sql,
                        {
                            "finished_lot": params.finished_lot,
                            "workshop_id": context.workshop_id,
                        },
                    )
                ).mappings().all()
            ]
        finally:
            await session.close()

        chain = [{"hop": 1, "source": "t_wip_detail", "records": wip_rows}]
        if mid_rows:
            chain.append({"hop": 2, "source": "t_wms_mid_item", "records": mid_rows})

        return TraceReverseResult(workshop_id=context.workshop_id, chain=chain)


get_inventory_status_tool = GetInventoryStatusTool()
guide_inbound_outbound_tool = GuideInboundOutboundTool()
profile_obsolete_inventory_tool = ProfileObsoleteInventoryTool()
trace_material_forward_tool = TraceMaterialForwardTool()
trace_product_reverse_tool = TraceProductReverseTool()
