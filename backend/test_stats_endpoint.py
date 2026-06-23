import asyncio
import sys
import os

async def test():
    try:
        from server import get_stats
        print("Imported server.py successfully.")
        res = await get_stats(current_user={"sub": "admin", "role": "admin"})
        print("RESULT:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
