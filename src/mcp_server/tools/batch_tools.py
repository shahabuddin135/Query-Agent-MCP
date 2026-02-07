"""Batch operation tools for MCP server.

This module implements batch operations:
- batch_delete_tasks: Delete multiple tasks at once (max 100)
- batch_update_tasks: Update multiple tasks at once (max 100)

All batch operations enforce the 100-item limit per SECURITY.md requirements.
"""

import logging
from typing import Optional
import asyncpg

logger = logging.getLogger("query-agent-mcp")


async def batch_delete_tasks(
    pool: asyncpg.Pool,
    user_id: int,
    task_ids: list[int]
) -> dict:
    """Delete multiple tasks in a single operation.
    
    Args:
        pool: Database connection pool
        user_id: User ID (for ownership verification)
        task_ids: List of task IDs to delete (max 100)
        
    Returns:
        dict: {success: bool, deleted_count: int, deleted_ids: list[int], message: str} or {error: str}
        
    Security:
        - Max 100 tasks per SECURITY.md
        - Only deletes tasks owned by user_id
    """
    try:
        # Enforce 100-item limit
        if len(task_ids) > 100:
            return {"error": "❌ Maximum 100 tasks allowed"}
        
        if not task_ids:
            return {"error": "❌ No task IDs provided"}
        
        async with pool.acquire() as conn:
            # Get IDs that will actually be deleted (for reporting)
            rows = await conn.fetch(
                "SELECT id FROM todos WHERE user_id = $1 AND id = ANY($2)",
                user_id, task_ids
            )
            deleted_ids = [row['id'] for row in rows]
            
            # Delete the tasks
            result = await conn.execute(
                "DELETE FROM todos WHERE user_id = $1 AND id = ANY($2)",
                user_id, task_ids
            )
            
            # Extract count from result string like "DELETE 3"
            deleted_count = int(result.split()[-1]) if result.split() else 0
            
            if deleted_count == 0:
                return {"error": "❌ No tasks found or not owned by user"}
            
            # Build message
            ids_str = ", ".join(f"#{id}" for id in deleted_ids)
            return {
                "success": True,
                "deleted_count": deleted_count,
                "deleted_ids": deleted_ids,
                "message": f"✅ Successfully deleted {deleted_count} task(s): {ids_str}"
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"batch_delete_tasks DB error: {e}")
        return {"error": "Database error while batch deleting tasks"}
    except Exception as e:
        logger.error(f"batch_delete_tasks error: {e}")
        return {"error": "Unexpected error while batch deleting tasks"}


async def batch_update_tasks(
    pool: asyncpg.Pool,
    user_id: int,
    task_ids: list[int],
    status: Optional[str] = None
) -> dict:
    """Update multiple tasks with the same values.
    
    Args:
        pool: Database connection pool
        user_id: User ID (for ownership verification)
        task_ids: List of task IDs to update (max 100)
        status: Optional new status (pending|in_progress|completed)
        
    Returns:
        dict: {success: bool, updated_count: int, updated_ids: list[int], message: str} or {error: str}
        
    Security:
        - Max 100 tasks per SECURITY.md
        - Only updates status and priority (limited fields)
        - Only updates tasks owned by user_id
    """
    try:
        # Enforce 100-item limit
        if len(task_ids) > 100:
            return {"error": "❌ Maximum 100 tasks allowed"}
        
        if not task_ids:
            return {"error": "❌ No task IDs provided"}
        
        # Require at least one field to update
        if status is None:
            return {"error": "❌ At least one field (status) must be provided"}
        
        async with pool.acquire() as conn:
            # Build dynamic UPDATE query
            updates = []
            params = [user_id, task_ids]
            param_counter = 3
            
            if status is not None:
                params.append(status)
                updates.append(f"status = ${param_counter}")
                param_counter += 1
            
            # Always set updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            # Build final query
            query = f"""
                UPDATE todos 
                SET {', '.join(updates)}
                WHERE user_id = $1 AND id = ANY($2)
                RETURNING id
            """
            
            rows = await conn.fetch(query, *params)
            updated_ids = [row['id'] for row in rows]
            updated_count = len(updated_ids)
            
            if updated_count == 0:
                return {"error": "❌ No tasks found or not owned by user"}
            
            # Build message
            ids_str = ", ".join(f"#{id}" for id in updated_ids)
            changes = []
            if status:
                changes.append(f"status={status}")
            changes_str = ", ".join(changes)
            
            return {
                "success": True,
                "updated_count": updated_count,
                "updated_ids": updated_ids,
                "message": f"✅ Updated {updated_count} task(s) ({changes_str}): {ids_str}"
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"batch_update_tasks DB error: {e}")
        return {"error": "Database error while batch updating tasks"}
    except Exception as e:
        logger.error(f"batch_update_tasks error: {e}")
        return {"error": "Unexpected error while batch updating tasks"}
