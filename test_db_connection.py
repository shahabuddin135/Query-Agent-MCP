"""Test script to verify database connection.

This script tests:
1. DATABASE_URL is configured
2. Connection pool can be created
3. Basic query execution works
4. Connection pool cleanup
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_database_connection():
    """Test database connection and basic query execution."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    # Import after environment is loaded
    from src.mcp_server import database
    
    try:
        # Step 1: Test DATABASE_URL is configured
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ FAILED: DATABASE_URL not configured in .env file")
            return False
        print(f"✓ DATABASE_URL configured: {db_url[:30]}...")
        
        # Step 2: Get database pool
        print("\nInitializing connection pool...")
        pool = await database.get_db_pool()
        print("✓ Connection pool created successfully")
        
        # Step 3: Test basic query execution
        print("\nTesting query execution...")
        async with pool.acquire() as conn:
            # Test query: Get database version
            result = await conn.fetchval("SELECT version()")
            print(f"✓ Query executed successfully")
            print(f"  PostgreSQL version: {result[:50]}...")
            
            # Test query: Count users
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            print(f"✓ Users table accessible: {user_count} users found")
            
            # Test query: Count todos
            todo_count = await conn.fetchval("SELECT COUNT(*) FROM todos")
            print(f"✓ Todos table accessible: {todo_count} todos found")
        
        # Step 4: Test pool cleanup
        print("\nCleaning up connection pool...")
        await database.close_db_pool()
        print("✓ Connection pool closed successfully")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print("1. Verify DATABASE_URL in .env is correct")
        print("2. Ensure Neon database is accessible")
        print("3. Check that users and todos tables exist")
        print("4. Verify SSL mode is enabled (sslmode=require)")
        return False


def main():
    """Entry point for test script."""
    success = asyncio.run(test_database_connection())
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
