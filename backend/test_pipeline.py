"""Full pipeline test: fetch -> clean -> metrics."""

import asyncio
import json
from app.monday_client import MondayClient
from app.data_cleaner import DataCleaner
from app.business_logic import MetricsEngine


async def test_pipeline():
    # 1. Fetch data
    print("=" * 60)
    print("1. FETCHING DATA FROM MONDAY.COM")
    print("=" * 60)
    client = MondayClient()
    data = await client.get_all_boards_data()
    print(f"   Deals: {len(data['deals']['items'])} items")
    print(f"   Work Orders: {len(data['work_orders']['items'])} items")

    # 2. Clean data
    print("\n" + "=" * 60)
    print("2. CLEANING & NORMALIZING DATA")
    print("=" * 60)
    cleaner = DataCleaner()
    board_data = cleaner.clean_board_data(
        deals_raw=data["deals"]["items"],
        work_orders_raw=data["work_orders"]["items"]
    )
    print(f"   Cleaned Deals: {len(board_data.deals)}")
    print(f"   Cleaned Work Orders: {len(board_data.work_orders)}")
    print(f"   Data Quality Warnings: {len(board_data.warnings)}")
    for w in board_data.warnings:
        print(f"     - [{w.severity}] {w.field}: {w.issue} ({w.affected_records} records)")

    # Sample cleaned data
    if board_data.deals:
        d = board_data.deals[0]
        print(f"\n   Sample Deal: {d.name}")
        print(f"     Sector: {d.sector}")
        print(f"     Value: {d.deal_value}")
        print(f"     Status: {d.status}")
        print(f"     Close Date: {d.close_date}")
        print(f"     Probability: {d.probability}")
        print(f"     Owner: {d.owner}")

    if board_data.work_orders:
        wo = board_data.work_orders[0]
        print(f"\n   Sample Work Order: {wo.name}")
        print(f"     Sector: {wo.sector}")
        print(f"     Invoiced: {wo.invoiced_amount}")
        print(f"     Collected: {wo.collected_amount}")
        print(f"     Status: {wo.status}")

    # 3. Compute Metrics
    print("\n" + "=" * 60)
    print("3. COMPUTING BUSINESS METRICS")
    print("=" * 60)
    engine = MetricsEngine(board_data)

    stats = engine.get_summary_stats()
    print(f"\n   Summary Stats:")
    for k, v in stats.items():
        print(f"     {k}: {v}")

    pipeline = engine.compute_total_pipeline_value()
    print(f"\n   Pipeline Value: {pipeline.formatted_value}")

    sector_breakdown = engine.compute_pipeline_by_sector()
    print(f"\n   Pipeline by Sector:\n{sector_breakdown.formatted_value}")

    ratio = engine.compute_deal_ratio()
    print(f"\n   Deal Ratio: {ratio.formatted_value}")

    inv_vs_col = engine.compute_invoiced_vs_collected()
    print(f"\n   Invoiced vs Collected: {inv_vs_col.formatted_value}")

    efficiency = engine.compute_collection_efficiency()
    print(f"\n   Collection Efficiency: {efficiency.formatted_value}")

    pvr = engine.compute_pipeline_vs_revenue()
    print(f"\n   Pipeline vs Revenue: {pvr.formatted_value}")

    print("\n" + "=" * 60)
    print("PIPELINE TEST COMPLETE")
    print("=" * 60)


asyncio.run(test_pipeline())
