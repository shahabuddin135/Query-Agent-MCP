"""Task management tools for MCP server.

This module implements the 6 core task management tools:
- create_task: Create a new task
- list_tasks: List all tasks for a user
- update_task: Update task details
- delete_task: Delete a task
- get_task_details: Get detailed information about a task
- search_tasks_by_keyword: Search tasks by keyword

All tools enforce user_id filtering per SECURITY.md requirements.
"""

import logging
from typing import Optional
import asyncpg

logger = logging.getLogger("query-agent-mcp")


async def create_task(
    pool: asyncpg.Pool,
    user_id: int,
    title: str,
    description: str = "",
    due_date: Optional[str] = None
) -> dict:
    """Create a new task.
    
    Args:
        pool: Database connection pool
        user_id: User ID who owns the task
        title: Task title
        description: Task description (optional)
        due_date: Due date in ISO 8601 format (optional)
        
    Returns:
        dict: {success: bool, task_id: int, message: str} or {error: str}
        
    Security:
        - All queries filter by user_id
        - Parameterized queries prevent SQL injection
        - created_by format: "task created by 'username'"
    """
    try:
        async with pool.acquire() as conn:
            # Step 1: Get username for created_by field
            username = await conn.fetchval(
                "SELECT username FROM users WHERE id = $1",
                user_id
            )
            
            if not username:
                return {"error": f"User {user_id} not found"}
            
            # Step 2: Format created_by per MEMORY.md D005
            created_by = f"task created by '{username}'"
            
            # Step 3: Insert task into todos table
            task_id = await conn.fetchval(
                """
                INSERT INTO todos (
                    user_id, title, description, status, due_date, created_by, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                user_id,
                title,
                description if description else None,
                "pending",  # Default status
                due_date,
                created_by
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "message": f"✅ Created task #{task_id}: '{title}'"
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"create_task DB error: {e}")
        return {"error": "Database error while creating task"}
    except Exception as e:
        logger.error(f"create_task error: {e}")
        return {"error": "Unexpected error while creating task"}


async def list_tasks(
    pool: asyncpg.Pool,
    user_id: int,
    status: Optional[str] = None
) -> dict:
    """List all tasks for a user with optional filtering.
    
    Args:
        pool: Database connection pool
        user_id: User ID
        status: Optional filter (pending|in_progress|completed)
        
    Returns:
        dict: {success: bool, count: int, tasks: list[dict]} or {error: str}
        
    Security:
        - Always filters by user_id
        - Sorts by created_at ASC per MEMORY.md D006
    """
    try:
        async with pool.acquire() as conn:
            # Build dynamic query based on filters
            query = "SELECT * FROM todos WHERE user_id = $1"
            params = [user_id]
            
            if status:
                params.append(status)
                query += f" AND status = ${len(params)}"
            
            # Always sort by created_at ASC (MEMORY.md D006)
            query += " ORDER BY created_at ASC"
            
            rows = await conn.fetch(query, *params)
            
            # Convert rows to dicts
            tasks = [dict(row) for row in rows]
            
            return {
                "success": True,
                "count": len(tasks),
                "tasks": tasks
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"list_tasks DB error: {e}")
        return {"error": "Database error while listing tasks"}
    except Exception as e:
        logger.error(f"list_tasks error: {e}")
        return {"error": "Unexpected error while listing tasks"}


async def update_task(
    pool: asyncpg.Pool,
    user_id: int,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None
) -> dict:
    """Update a task with optional field updates.
    
    Args:
        pool: Database connection pool
        user_id: User ID (for ownership verification)
        task_id: Task ID to update
        title: Optional new title
        description: Optional new description
        status: Optional new status (pending|in_progress|completed)
        due_date: Optional new due date or 'none' to clear
        
    Returns:
        dict: {success: bool, task: dict, message: str} or {error: str}
        
    Security:
        - Verifies ownership (WHERE user_id = $1 AND id = $2)
        - Only updates provided fields
        - Auto-sets updated_at timestamp
    """
    try:
        async with pool.acquire() as conn:
            # Build dynamic UPDATE query
            updates = []
            params = [user_id, task_id]
            param_counter = 3  # Start after user_id and task_id
            
            if title is not None:
                params.append(title)
                updates.append(f"title = ${param_counter}")
                param_counter += 1
                
            if description is not None:
                params.append(description)
                updates.append(f"description = ${param_counter}")
                param_counter += 1
                
            if status is not None:
                params.append(status)
                updates.append(f"status = ${param_counter}")
                param_counter += 1
                
            if due_date is not None:
                if due_date.lower() == 'none':
                    updates.append("due_date = NULL")
                else:
                    params.append(due_date)
                    updates.append(f"due_date = ${param_counter}")
                    param_counter += 1
            
            # Require at least one field to update
            if not updates:
                return {"error": "At least one field must be provided for update"}
            
            # Always set updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            # Build final query
            query = f"""
                UPDATE todos 
                SET {', '.join(updates)}
                WHERE user_id = $1 AND id = $2
                RETURNING *
            """
            
            row = await conn.fetchrow(query, *params)
            
            if not row:
                return {"error": f"Task #{task_id} not found or not owned by user {user_id}"}
            
            task = dict(row)
            return {
                "success": True,
                "task": task,
                "message": f"✅ Updated task #{task_id}"
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"update_task DB error: {e}")
        return {"error": "Database error while updating task"}
    except Exception as e:
        logger.error(f"update_task error: {e}")
        return {"error": "Unexpected error while updating task"}


async def delete_task(
    pool: asyncpg.Pool,
    user_id: int,
    task_id: int
) -> dict:
    """Delete a task.
    
    Args:
        pool: Database connection pool
        user_id: User ID (for ownership verification)
        task_id: Task ID to delete
        
    Returns:
        dict: {success: bool, deleted_id: int, message: str} or {error: str}
        
    Security:
        - Verifies ownership (WHERE user_id = $1 AND id = $2)
    """
    try:
        async with pool.acquire() as conn:
            # Get title before deletion for message
            row = await conn.fetchrow(
                "SELECT title FROM todos WHERE user_id = $1 AND id = $2",
                user_id, task_id
            )
            
            if not row:
                return {"error": f"❌ Task #{task_id} not found or not owned by user {user_id}"}
            
            title = row['title']
            
            # Delete the task
            await conn.execute(
                "DELETE FROM todos WHERE user_id = $1 AND id = $2",
                user_id, task_id
            )
            
            return {
                "success": True,
                "deleted_id": task_id,
                "message": f"✅ Deleted task #{task_id}: '{title}'"
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"delete_task DB error: {e}")
        return {"error": "Database error while deleting task"}
    except Exception as e:
        logger.error(f"delete_task error: {e}")
        return {"error": "Unexpected error while deleting task"}


async def get_task_details(
    pool: asyncpg.Pool,
    user_id: int,
    task_id: int
) -> dict:
    """Get detailed information about a specific task.
    
    Args:
        pool: Database connection pool
        user_id: User ID (for ownership verification)
        task_id: Task ID to retrieve
        
    Returns:
        dict: {success: bool, task: dict} or {error: str}
        
    Security:
        - Only returns tasks owned by user_id
    """
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM todos WHERE user_id = $1 AND id = $2",
                user_id, task_id
            )
            
            if not row:
                return {"error": f"❌ Task #{task_id} not found or not owned by user {user_id}"}
            
            task = dict(row)
            return {
                "success": True,
                "task": task
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"get_task_details DB error: {e}")
        return {"error": "Database error while fetching task details"}
    except Exception as e:
        logger.error(f"get_task_details error: {e}")
        return {"error": "Unexpected error while fetching task details"}


async def search_tasks_by_keyword(
    pool: asyncpg.Pool,
    user_id: int,
    keyword: str
) -> dict:
    """Search tasks by keyword in title and description.
    
    Args:
        pool: Database connection pool
        user_id: User ID
        keyword: Search keyword (case-insensitive)
        
    Returns:
        dict: {success: bool, count: int, tasks: list[dict]} or {error: str}
        
    Security:
        - Always filters by user_id
        - Case-insensitive ILIKE search
        - Sorted by created_at ASC per MEMORY.md D006
    """
    try:
        async with pool.acquire() as conn:
            # Wrap keyword with % for ILIKE pattern matching
            pattern = f"%{keyword}%"
            
            rows = await conn.fetch(
                """SELECT * FROM todos 
                   WHERE user_id = $1 
                   AND (title ILIKE $2 OR description ILIKE $2)
                   ORDER BY created_at ASC""",
                user_id, pattern
            )
            
            tasks = [dict(row) for row in rows]
            
            return {
                "success": True,
                "count": len(tasks),
                "tasks": tasks
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"search_tasks_by_keyword DB error: {e}")
        return {"error": "Database error while searching tasks"}
    except Exception as e:
        logger.error(f"search_tasks_by_keyword error: {e}")
        return {"error": "Unexpected error while searching tasks"}
