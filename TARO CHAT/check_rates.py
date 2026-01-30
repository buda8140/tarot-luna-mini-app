
import asyncio
from database import db

async def check_rates():
    rates = await db.get_all_rates()
    print("Current rates in DB:")
    for rate in rates:
        print(f"Key: {rate['package_key']}, Price: {rate['price']}, Label: {rate['label']}")

if __name__ == "__main__":
    asyncio.run(check_rates())
