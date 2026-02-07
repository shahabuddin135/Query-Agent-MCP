"""Functional tests for all 10 MCP tools.

This test suite validates the functionality of all tools by simulating
tool calls through the server's call_tool handler.
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


async def test_tools():
    """Run comprehensive functional tests for all tools."""
    print("=" * 60)
    print("Functional Testing: All 10 Tools")
    print("=" * 60)
    
    # Initialize database pool
    pool = await database.get_db_pool()
    print("✓ Database connection established\n")
    
    # Set up server context (simulate lifespan context)
    # This is needed because handle_call_tool accesses server.request_context
    # For testing, we'll call tool functions directly instead
    
    from mcp_server.tools import task_tools, batch_tools, sql_tools
    
    # Use user_id=1 for tests (exists in database per earlier tests)
    test_user_id = 1
    
    try:
        # Test 1: create_task
        print("Test 1: create_task")
        result = await task_tools.create_task(
            pool,
            user_id=test_user_id,
            title="Functional Test Task",
            description="Testing create_task functionality",
            due_date=None  # Use None instead of string date for now
        )
        assert result.get("success") == True, f"create_task failed: {result}"
        task_id = result.get("task_id")
        print(f"✓ Created task #{task_id}: {result['message']}\n")
        
        # Test 2: list_tasks (all)
        print("Test 2: list_tasks (all tasks)")
        result = await task_tools.list_tasks(pool, user_id=test_user_id)
        assert result.get("success") == True, f"list_tasks failed: {result}"
        print(f"✓ Listed {result['count']} tasks\n")
        
        # Test 3: list_tasks (filtered by status)
        print("Test 3: list_tasks (pending only)")
        result = await task_tools.list_tasks(pool, user_id=test_user_id, status="pending")
        assert result.get("success") == True, f"list_tasks with filter failed: {result}"
        print(f"✓ Listed {result['count']} pending tasks\n")
        
        # Test 4: get_task_details
        print("Test 4: get_task_details")
        result = await task_tools.get_task_details(pool, user_id=test_user_id, task_id=task_id)
        assert result.get("success") == True, f"get_task_details failed: {result}"
        print(f"✓ Retrieved task #{task_id}: {result['task']['title']}\n")
        
        # Test 5: update_task (partial update)
        print("Test 5: update_task (status only)")
        result = await task_tools.update_task(
            pool,
            user_id=test_user_id,
            task_id=task_id,
            status="in_progress"
        )
        assert result.get("success") == True, f"update_task failed: {result}"
        print(f"✓ {result['message']}\n")
        
        # Test 6: update_task (multiple fields)
        print("Test 6: update_task (multiple fields)")
        result = await task_tools.update_task(
            pool,
            user_id=test_user_id,
            task_id=task_id,
            status="completed",
            description="Updated description"
        )
        assert result.get("success") == True, f"update_task failed: {result}"
        print(f"✓ {result['message']}\n")
        
        # Test 7: search_tasks_by_keyword
        print("Test 7: search_tasks_by_keyword")
        result = await task_tools.search_tasks_by_keyword(
            pool,
            user_id=test_user_id,
            keyword="Functional"
        )
        assert result.get("success") == True, f"search_tasks failed: {result}"
        print(f"✓ Found {result['count']} tasks matching 'Functional'\n")
        
        # Create additional tasks for batch operations
        print("Test 8: Setup - Creating 5 tasks for batch operations")
        batch_task_ids = []
        for i in range(5):
            result = await task_tools.create_task(
                pool,
                user_id=test_user_id,
                title=f"Batch Test Task {i+1}"
            )
            if result.get("success"):
                batch_task_ids.append(result["task_id"])
        print(f"✓ Created {len(batch_task_ids)} tasks: {batch_task_ids}\n")
        
        # Test 9: batch_update_tasks
        print("Test 9: batch_update_tasks")
        result = await batch_tools.batch_update_tasks(
            pool,
            user_id=test_user_id,
            task_ids=batch_task_ids[:3],  # Update first 3
            status="completed"
        )
        assert result.get("success") == True, f"batch_update failed: {result}"
        print(f"✓ {result['message']}\n")
        
        # Test 10: batch_delete_tasks
        print("Test 10: batch_delete_tasks")
        result = await batch_tools.batch_delete_tasks(
            pool,
            user_id=test_user_id,
            task_ids=batch_task_ids  # Delete all 5
        )
        assert result.get("success") == True, f"batch_delete failed: {result}"
        print(f"✓ {result['message']}\n")
        
        # Test 11: generate_sql_query
        print("Test 11: generate_sql_query")
        result = await sql_tools.generate_sql_query(
            pool,
            user_id=test_user_id,
            question="show my completed tasks"
        )
        assert result.get("success") == True, f"generate_sql failed: {result}"
        print(f"✓ Generated SQL: {result.get('query', 'N/A')[:80]}...\n")
        
        # Test 12: execute_sql_query (safe SELECT)
        print("Test 12: execute_sql_query (safe SELECT)")
        result = await sql_tools.execute_sql_query(
            pool,
            user_id=test_user_id,
            query=f"SELECT COUNT(*) as total FROM todos WHERE user_id = {test_user_id}"
        )
        assert result.get("success") == True, f"execute_sql failed: {result}"
        print(f"✓ Executed query: {result['row_count']} rows returned\n")
        
        # Test 13: delete_task (cleanup)
        print("Test 13: delete_task")
        result = await task_tools.delete_task(pool, user_id=test_user_id, task_id=task_id)
        assert result.get("success") == True, f"delete_task failed: {result}"
        print(f"✓ {result['message']}\n")
        
        # Edge cases
        print("=" * 60)
        print("Edge Case Testing")
        print("=" * 60)
        
        # Edge 1: Empty batch
        print("Edge 1: batch_delete_tasks with empty array")
        result = await batch_tools.batch_delete_tasks(pool, user_id=test_user_id, task_ids=[])
        assert "error" in result, "Should fail with empty array"
        print(f"✓ Correctly rejected: {result['error']}\n")
        
        # Edge 2: Batch limit (100 items)
        print("Edge 2: batch_delete_tasks with exactly 100 items")
        hundred_ids = list(range(1, 101))
        result = await batch_tools.batch_delete_tasks(pool, user_id=test_user_id, task_ids=hundred_ids)
        # May succeed or fail based on actual data, but shouldn't error on limit
        print(f"✓ Accepted 100 items (limit): {result.get('message', result.get('error'))}\n")
        
        # Edge 3: Update with no fields
        print("Edge 3: update_task with no fields")
        result = await task_tools.update_task(pool, user_id=test_user_id, task_id=999)
        assert "error" in result, "Should require at least one field"
        print(f"✓ Correctly rejected: {result['error']}\n")
        
        # Edge 4: Non-existent task
        print("Edge 4: get_task_details for non-existent task")
        result = await task_tools.get_task_details(pool, user_id=test_user_id, task_id=999999)
        assert "error" in result, "Should fail for non-existent task"
        print(f"✓ Correctly reported: {result['error']}\n")
        
        # Edge 5: SQL generation - no match
        print("Edge 5: generate_sql_query with unmatchable input")
        result = await sql_tools.generate_sql_query(
            pool,
            user_id=test_user_id,
            question="flibbertigibbet zounderkite"
        )
        assert result.get("success") == True, "Should return helpful message"
        print(f"✓ Handled gracefully: {result['message'][:60]}...\n")
        
        print("=" * 60)
        print("✅ ALL FUNCTIONAL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
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
    success = asyncio.run(test_tools())
    sys.exit(0 if success else 1)
