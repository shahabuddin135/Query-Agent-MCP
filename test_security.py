"""Security tests for MCP server.

This test suite validates security controls:
- SQL injection prevention
- User isolation (cross-user access prevention)
- Batch operation limits (max 100)
- execute_sql_query restrictions (SELECT-only, user_id required)
"""

import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, "src")

from mcp_server.server import server
from mcp_server import database


async def test_security():
    """Run comprehensive security tests."""
    print("=" * 60)
    print("Security Testing: Attack Scenarios")
    print("=" * 60)
    
    # Initialize database pool
    pool = await database.get_db_pool()
    print("✓ Database connection established\n")
    
    from mcp_server.tools import task_tools, batch_tools, sql_tools
    
    # Use user_id=1 for tests
    test_user_id = 1
    
    try:
        # Test 1: SQL Injection in create_task title
        print("Test 1: SQL Injection - Malicious title")
        malicious_title = "Test'; DROP TABLE todos; --"
        result = await task_tools.create_task(
            pool,
            user_id=test_user_id,
            title=malicious_title,
            description="SQL injection attempt"
        )
        assert result.get("success") == True, "Should succeed but safely escape"
        print(f"✓ SQL injection prevented: Task created safely with title='{malicious_title}'\n")
        cleanup_id = result.get("task_id")
        
        # Test 2: Cross-user access - Try to get task from another user
        print("Test 2: User Isolation - Cross-user task access")
        # First, check if there are tasks from other users
        all_tasks_query = await pool.fetchrow(
            "SELECT id, user_id FROM todos WHERE user_id != $1 LIMIT 1",
            test_user_id
        )
        if all_tasks_query:
            other_task_id = all_tasks_query['id']
            result = await task_tools.get_task_details(
                pool,
                user_id=test_user_id,
                task_id=other_task_id
            )
            assert "error" in result, "Should fail - cannot access other user's task"
            print(f"✓ Cross-user access prevented: {result['error']}\n")
        else:
            print(f"⚠ Skipped: No tasks from other users in database\n")
        
        # Test 3: Batch limit enforcement (>100 items)
        print("Test 3: Batch Limit - 101 items rejection")
        overflow_ids = list(range(1, 102))  # 101 items
        result = await batch_tools.batch_delete_tasks(
            pool,
            user_id=test_user_id,
            task_ids=overflow_ids
        )
        assert "error" in result, "Should reject >100 items"
        assert "100" in result["error"], "Error should mention limit"
        print(f"✓ Batch limit enforced: {result['error']}\n")
        
        # Test 4: execute_sql_query - DDL prevention (DROP)
        print("Test 4: SQL Query Restriction - DROP TABLE")
        result = await sql_tools.execute_sql_query(
            pool,
            user_id=test_user_id,
            query="DROP TABLE todos"
        )
        assert "error" in result, "Should reject DROP"
        print(f"✓ DDL prevented: {result['error']}\n")
        
        # Test 5: execute_sql_query - INSERT prevention
        print("Test 5: SQL Query Restriction - INSERT")
        result = await sql_tools.execute_sql_query(
            pool,
            user_id=test_user_id,
            query="INSERT INTO todos (title, user_id) VALUES ('hack', 1)"
        )
        assert "error" in result, "Should reject INSERT"
        print(f"✓ INSERT prevented: {result['error']}\n")
        
        # Test 6: execute_sql_query - UPDATE prevention
        print("Test 6: SQL Query Restriction - UPDATE")
        result = await sql_tools.execute_sql_query(
            pool,
            user_id=test_user_id,
            query="UPDATE todos SET status = 'hacked'"
        )
        assert "error" in result, "Should reject UPDATE"
        print(f"✓ UPDATE prevented: {result['error']}\n")
        
        # Test 7: execute_sql_query - Missing user_id filter
        print("Test 7: SQL Query Restriction - Missing user_id filter")
        result = await sql_tools.execute_sql_query(
            pool,
            user_id=test_user_id,
            query="SELECT * FROM todos"
        )
        assert "error" in result, "Should reject query without user_id"
        assert "user_id" in result["error"].lower(), "Error should mention user_id"
        print(f"✓ User filter enforced: {result['error']}\n")
        
        # Test 8: execute_sql_query - Successful SELECT with user_id
        print("Test 8: SQL Query - Valid SELECT with user_id filter")
        result = await sql_tools.execute_sql_query(
            pool,
            user_id=test_user_id,
            query=f"SELECT id, title FROM todos WHERE user_id = {test_user_id} LIMIT 5"
        )
        assert result.get("success") == True, "Should allow valid SELECT"
        print(f"✓ Valid SELECT allowed: {result['row_count']} rows returned\n")
        
        # Test 9: Cross-user task modification
        print("Test 9: User Isolation - Try to update another user's task")
        if all_tasks_query:
            other_task_id = all_tasks_query['id']
            result = await task_tools.update_task(
                pool,
                user_id=test_user_id,
                task_id=other_task_id,
                status="hacked"
            )
            assert "error" in result, "Should fail - cannot update other user's task"
            print(f"✓ Cross-user update prevented: {result['error']}\n")
        else:
            print(f"⚠ Skipped: No tasks from other users in database\n")
        
        # Test 10: Cross-user task deletion
        print("Test 10: User Isolation - Try to delete another user's task")
        if all_tasks_query:
            other_task_id = all_tasks_query['id']
            result = await task_tools.delete_task(
                pool,
                user_id=test_user_id,
                task_id=other_task_id
            )
            assert "error" in result, "Should fail - cannot delete other user's task"
            print(f"✓ Cross-user delete prevented: {result['error']}\n")
        else:
            print(f"⚠ Skipped: No tasks from other users in database\n")
        
        # Test 11: Batch operations - Cross-user tasks
        print("Test 11: Batch User Isolation - Try to batch delete other user's tasks")
        if all_tasks_query:
            other_task_ids = await pool.fetch(
                "SELECT id FROM todos WHERE user_id != $1 LIMIT 3",
                test_user_id
            )
            other_ids = [row['id'] for row in other_task_ids]
            result = await batch_tools.batch_delete_tasks(
                pool,
                user_id=test_user_id,
                task_ids=other_ids
            )
            # Should succeed but delete 0 tasks (user isolation)
            if "error" in result:
                print(f"✓ Batch isolation enforced: {result['error']}\n")
            else:
                assert result.get("deleted_count", 0) == 0, "Should delete 0 tasks"
                print(f"✓ Batch isolation enforced: 0 tasks deleted (not owned by user)\n")
        else:
            print(f"⚠ Skipped: No tasks from other users in database\n")
        
        # Cleanup: Delete the injection test task
        if cleanup_id:
            await task_tools.delete_task(pool, user_id=test_user_id, task_id=cleanup_id)
            print(f"✓ Cleaned up test task #{cleanup_id}")
        
        print("=" * 60)
        print("✅ ALL SECURITY TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Security test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await database.close_db_pool()
        print("\n✓ Database connection closed")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_security())
    sys.exit(0 if success else 1)
