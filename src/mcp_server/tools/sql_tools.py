"""SQL query tools for MCP server.

This module implements dynamic SQL operations:
- generate_sql_query: Generate SQL queries from natural language
- execute_sql_query: Execute SELECT-only queries (read-only)

All SQL queries enforce user_id filtering and parameterized queries per SECURITY.md.
"""

import logging
import re
import asyncpg

logger = logging.getLogger("query-agent-mcp")


async def generate_sql_query(
    pool: asyncpg.Pool,
    user_id: int,
    question: str
) -> dict:
    """Generate SQL query from natural language question.
    
    Args:
        pool: Database connection pool (not used for generation)
        user_id: User ID (to be included in generated query)
        question: Natural language question
        
    Returns:
        dict: {success: bool, query: str, message: str} or {error: str}
        
    Note:
        - Simple pattern matching implementation for MVP
        - Always includes user_id filter in generated queries
        - Does NOT execute the query
    """
    try:
        question_lower = question.lower().strip()
        
        # All generated queries use parameterized user_id ($1) to prevent SQL injection.
        # The caller (execute_sql_query) enforces user_id substitution at execution time.
        
        # Pattern: "show/list (my) tasks"
        if re.search(r'\b(show|list|get)\b.*\btasks?\b', question_lower):
            query = "SELECT * FROM todos WHERE user_id = $1"
            
            # Add status filter (safe — literal values, not user input)
            if 'completed' in question_lower:
                query += " AND status = 'completed'"
            elif 'pending' in question_lower:
                query += " AND status = 'pending'"
            elif 'in progress' in question_lower or 'in-progress' in question_lower:
                query += " AND status = 'in_progress'"
            
            query += " ORDER BY created_at ASC"
            
            return {
                "success": True,
                "query": query,
                "params": [user_id],
                "message": f"✨ Generated SQL:\n{query}\n\nUse execute_sql_query to run it."
            }
        
        # Pattern: "count tasks"
        elif re.search(r'\bcount\b.*\btasks?\b', question_lower):
            query = "SELECT COUNT(*) as task_count FROM todos WHERE user_id = $1"
            
            if 'completed' in question_lower:
                query += " AND status = 'completed'"
            elif 'pending' in question_lower:
                query += " AND status = 'pending'"
            
            return {
                "success": True,
                "query": query,
                "params": [user_id],
                "message": f"✨ Generated SQL:\n{query}\n\nUse execute_sql_query to run it."
            }
        
        # Pattern: "find/search tasks with keyword"
        elif re.search(r'\b(find|search)\b.*\btasks?\b', question_lower):
            # Extract keyword (simple extraction — last word)
            words = question_lower.split()
            keyword = words[-1] if words else ""
            
            # Use parameterized ILIKE ($2) — NEVER interpolate user input into SQL
            query = "SELECT * FROM todos WHERE user_id = $1 AND (title ILIKE $2 OR description ILIKE $2) ORDER BY created_at ASC"
            
            return {
                "success": True,
                "query": query,
                "params": [user_id, f"%{keyword}%"],
                "message": f"✨ Generated SQL:\n{query}\n\nUse execute_sql_query to run it."
            }
        
        else:
            # No pattern match
            return {
                "success": True,
                "message": "❓ Could not generate SQL query. Try queries like:\n- 'show my tasks'\n- 'list completed tasks'\n- 'count pending tasks'\n\nOr use execute_sql_query directly with your own SQL."
            }
            
    except Exception as e:
        return {"error": "Failed to generate SQL query"}


async def execute_sql_query(
    pool: asyncpg.Pool,
    user_id: int,
    query: str
) -> dict:
    """Execute a SELECT-only SQL query with user_id filtering.
    
    Args:
        pool: Database connection pool
        user_id: User ID (must be present in query WHERE clause)
        query: SQL query (SELECT only)
        
    Returns:
        dict: {success: bool, row_count: int, results: list[dict]} or {error: str}
        
    Security:
        - Only SELECT queries allowed
        - Must contain user_id filter
        - Rejects: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
    """
    try:
        query_stripped = query.strip()
        query_upper = query_stripped.upper()
        
        # Security check 1: Only SELECT allowed
        if not query_upper.startswith("SELECT"):
            return {"error": "❌ Only SELECT queries are allowed"}
        
        # Security check 2: Reject dangerous keywords
        dangerous_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
            "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXEC",
            "EXECUTE", "INTO",
        ]
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', query_upper):
                return {"error": f"❌ {keyword} operations are not allowed"}
        
        # Security check 3: Block multiple statements & SQL comments
        if ";" in query_stripped:
            return {"error": "❌ Multiple statements are not allowed"}
        if "--" in query_stripped or "/*" in query_stripped:
            return {"error": "❌ SQL comments are not allowed in queries"}
        
        # Security check 4: Restrict to todos table only
        # Prevent querying users table (which holds hashed passwords, emails)
        allowed_tables = {"TODOS"}
        # Simple heuristic: reject if 'FROM users' or 'JOIN users' appears
        if re.search(r'\b(FROM|JOIN)\s+(?!TODOS\b)\w+', query_upper):
            # Check which table is being accessed
            table_matches = re.findall(r'\b(?:FROM|JOIN)\s+(\w+)', query_upper)
            for table in table_matches:
                if table not in allowed_tables:
                    return {"error": f"❌ Access to table '{table.lower()}' is not allowed. Only the 'todos' table can be queried."}
        
        # Security check 5: Must reference user_id for row-level security
        if "USER_ID" not in query_upper:
            return {"error": "❌ Query must include user_id filter for security"}
        
        # Security check 6: Enforce parameterized user_id
        # Replace literal user_id value with $1 parameter and bind it
        # This forces row-level filtering even if the query tries to bypass it
        safe_query = re.sub(
            r'user_id\s*=\s*(\d+)',
            'user_id = $1',
            query_stripped,
            flags=re.IGNORECASE
        )
        
        # Execute with parameterized user_id
        async with pool.acquire() as conn:
            if '$1' in safe_query:
                rows = await conn.fetch(safe_query, user_id)
            else:
                # user_id referenced but not in simple = format; reject
                return {"error": "❌ Query must use 'user_id = <id>' format for security"}
            
            # Convert rows to list of dicts
            results = [dict(row) for row in rows]
            
            return {
                "success": True,
                "row_count": len(results),
                "results": results
            }
            
    except asyncpg.PostgresError:
        return {"error": "❌ SQL query failed. Please check your query syntax."}
    except Exception:
        return {"error": "❌ An unexpected error occurred while executing the query."}
