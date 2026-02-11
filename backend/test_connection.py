"""Quick test script to verify monday.com API connectivity."""

import asyncio
from app.monday_client import MondayClient


async def test():
    client = MondayClient()
    data = await client.get_all_boards_data()
    
    deals = data["deals"]["items"]
    work_orders = data["work_orders"]["items"]
    
    print(f"Deals: {len(deals)} items")
    print(f"Work Orders: {len(work_orders)} items")
    
    if deals:
        print(f"\nDeal sample keys: {list(deals[0].keys())}")
        print(f"\nFirst deal: {deals[0]['name']}")
        for k, v in deals[0].items():
            if v is not None and k not in ("raw_data",):
                print(f"  {k}: {v}")
    
    if work_orders:
        print(f"\nFirst work order: {work_orders[0]['name']}")
        for k, v in work_orders[0].items():
            if v is not None and k not in ("raw_data",):
                print(f"  {k}: {v}")


asyncio.run(test())
