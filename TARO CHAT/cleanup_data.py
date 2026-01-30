
import asyncio
import sqlite3
import os
from database import db
from config import DB_PATH

async def cleanup():
    print(f"Connecting to database at {DB_PATH}")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 1. Удаляем buy_test из rates
            cursor.execute("DELETE FROM rates WHERE package_key = 'buy_test'")
            rates_deleted = cursor.rowcount
            print(f"Deleted {rates_deleted} rates with key 'buy_test'")
            
            # 2. Удаляем pending платежи старше 7 дней или связанные с buy_test
            # Сначала buy_test
            cursor.execute("DELETE FROM payments WHERE yoomoney_label LIKE '%pkg_buy_test%' OR yoomoney_label LIKE '%buy_test%'")
            test_payments_deleted = cursor.rowcount
            print(f"Deleted {test_payments_deleted} payments related to 'buy_test'")
            
            # Затем старые pending (через метод класса для надежности, но можно и SQL)
            # Используем прямой SQL для гарантии
            cursor.execute("""
                DELETE FROM payments 
                WHERE status = 'pending' 
                AND datetime(timestamp) < datetime('now', '-7 days')
            """)
            old_pending_deleted = cursor.rowcount
            print(f"Deleted {old_pending_deleted} old pending payments (> 7 days)")
            
            conn.commit()
            print("Cleanup completed successfully.")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
    else:
        asyncio.run(cleanup())
