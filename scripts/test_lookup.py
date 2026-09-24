import asyncio
from app.repositories.order_lookup import OrderLookup, detect_features

async def main():
    info = await OrderLookup().find_order("001-00006-01-1")
    print(info)
    if info:
        print("Features:", detect_features(info.description))

asyncio.run(main())