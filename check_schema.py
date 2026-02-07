"""Quick script to check todos table schema."""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from src.mcp_server.database import get_db_pool, close_db_pool

async def check_schema():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'todos' ORDER BY ordinal_position"
        )
        print("\nTodos table columns:")
        for r in result:
            print(f"  {r['column_name']}: {r['data_type']}")
    await close_db_pool()

asyncio.run(check_schema())
