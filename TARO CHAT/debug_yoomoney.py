
import asyncio
from yoomoney import YooMoneyPayment
import logging

# Configure basic logging to see output
logging.basicConfig(level=logging.INFO)

async def check_history():
    ym = YooMoneyPayment()
    print(f"Checking history for wallet: {ym.wallet}")
    print(f"Token (masked): {ym.token[:5]}...{ym.token[-5:] if ym.token else 'None'}")
    
    try:
        # Fetch last 1 hour of operations
        history = await ym.get_recent_operations(hours=1)
        print(f"Found {len(history)} operations in the last hour.")
        
        for op in history:
            print("-" * 50)
            print(f"Operation ID: {op.get('operation_id')}")
            print(f"Status: {op.get('status')}")
            print(f"Direction: {op.get('direction')}")
            print(f"Amount: {op.get('amount')}")
            print(f"Datetime: {op.get('datetime')}")
            print(f"Label: {op.get('label')}")
            print(f"Details: {op.get('details')}")
            print(f"Title: {op.get('title')}")
            
    except Exception as e:
        print(f"Error fetching history: {e}")

if __name__ == "__main__":
    asyncio.run(check_history())
