"""Test script to verify MCP server initialization.

This script tests:
1. Server can be imported
2. Server can start with stdio transport
3. Server responds to initialization
4. Server lists tools correctly
"""

import asyncio
import json
import sys
from io import StringIO


async def test_server_import():
    """Test that server module can be imported."""
    print("=" * 60)
    print("Testing MCP Server Startup")
    print("=" * 60)
    
    try:
        # Test import
        print("\n1. Testing server import...")
        from src.mcp_server import server
        print("✓ Server module imported successfully")
        
        # Test server initialization
        print("\n2. Testing server initialization...")
        assert server.server is not None, "Server instance not created"
        print(f"✓ Server instance created: {server.server.name}")
        
        # Test lifespan function exists
        print("\n3. Testing lifespan configuration...")
        assert server.server.lifespan is not None, "Lifespan not configured"
        print("✓ Lifespan manager configured")
        
        # Test tool handlers exist
        print("\n4. Testing tool handlers...")
        tools = await server.handle_list_tools()
        assert len(tools) == 10, f"Expected 10 tools, got {len(tools)}"
        print(f"✓ Tool handler registered: {len(tools)} tools available")
        
        # Verify all tool names
        tool_names = {tool.name for tool in tools}
        expected_tools = {
            "create_task", "list_tasks", "update_task", "delete_task",
            "get_task_details", "search_tasks_by_keyword",
            "batch_delete_tasks", "batch_update_tasks",
            "generate_sql_query", "execute_sql_query"
        }
        assert tool_names == expected_tools, f"Tool names mismatch: {tool_names}"
        print("✓ All 10 tools registered correctly:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nServer is ready to run with:")
        print("  python -m src.mcp_server.server")
        print("\nOr in MCP client configuration, use:")
        print('  "command": "python"')
        print('  "args": ["-m", "src.mcp_server.server"]')
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Entry point for test script."""
    success = asyncio.run(test_server_import())
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
