"""Database connection pool management for PostgreSQL using asyncpg.

This module provides a singleton connection pool that manages database connections
for the MCP server. The pool is initialized once at server startup and reused
throughout the application lifecycle.

Security Notes:
    - All queries MUST filter by user_id (enforced at the tool level)
    - Connection uses DATABASE_URL from environment variables
    - SSL mode is required for Neon database connections
"""

import os
import asyncpg
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Global connection pool instance
_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create the database connection pool.
    
    Returns a singleton asyncpg connection pool configured for Neon PostgreSQL.
    The pool is created on first call and reused for subsequent calls.
    
    Pool Configuration:
        - min_size: 1 (minimum connections to maintain)
        - max_size: 10 (maximum concurrent connections)
        - command_timeout: 30 seconds (query timeout)
        - sslmode: require (enforced for Neon)
        
    Returns:
        asyncpg.Pool: Configured database connection pool
        
    Raises:
        ValueError: If DATABASE_URL environment variable is not set
        asyncpg.exceptions.PostgresError: If connection cannot be established
        
    Example:
        ```python
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetch("SELECT * FROM todos WHERE user_id = $1", user_id)
        ```
    """
    global _pool
    
    if _pool is not None:
        return _pool
    
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please configure the .env file with your Neon database connection string."
        )
    
    # Create the connection pool with asyncpg.create_pool
    # Using min_size=1, max_size=10 per ARCH.md specifications
    _pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=1,
        max_size=10,
        command_timeout=30.0,  # 30 second timeout for queries
        # Neon requires SSL, ensure it's enabled
        # (connection string should include sslmode=require)
    )
    
    return _pool


async def close_db_pool() -> None:
    """Close the database connection pool gracefully.
    
    This should be called during server shutdown to ensure all connections
    are properly released and closed. Waits for all active connections to
    be released before closing the pool.
    
    Example:
        ```python
        # During server shutdown
        await close_db_pool()
        ```
    """
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
