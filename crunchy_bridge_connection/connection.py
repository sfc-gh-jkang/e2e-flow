"""Crunchy Bridge PostgreSQL connection management.

    This module provides utilities for connecting to Crunchy Bridge PostgreSQL.
    It uses the psycopg library to connect to the database and provides a connection string and a function to get a connection.
    It also provides a function to test the connection.

    Environment variables are checked first, then falls back to Prefect Blocks/Variables.

    To test this module run: uv run -m crunchy_bridge_connection.connection
"""

import os

import psycopg
from dotenv import load_dotenv
from psycopg import Connection
from prefect.blocks.system import Secret
from prefect.variables import Variable

# Auto-load .env file if present
load_dotenv()

# Define schema names
postgres_schema = "eve_online"
# Define table names
eve_market_data_table = "eve_market_data"


def get_env_or_prefect(
    env_name: str, 
    prefect_name: str, 
    is_secret: bool = False, 
    default: str | None = None,
    use_prefect_only: bool = False,
) -> str | None:
    """Get value from environment variable, fall back to Prefect Block/Variable.
    
    Args:
        env_name: Environment variable name (e.g., "PGHOST")
        prefect_name: Prefect Block/Variable name (e.g., "pghost")
        is_secret: If True, use Prefect Secret block; if False, use Variable
        default: Default value if not found in env or Prefect
        use_prefect_only: If True, skip env vars and only use Prefect
        
    Returns:
        The value from env, Prefect, or default
        
    Priority (when use_prefect_only=False):
        1. Environment variable
        2. Prefect Secret (if is_secret=True) or Variable
        3. Default value
        
    Priority (when use_prefect_only=True):
        1. Prefect Secret (if is_secret=True) or Variable
        2. Default value
    """
    # Check environment variable first (unless use_prefect_only)
    if not use_prefect_only:
        value = os.getenv(env_name)
        if value:
            return value
    
    # Fallback to Prefect (or primary if use_prefect_only)
    try:
        if is_secret:
            return Secret.load(prefect_name).get()
        else:
            return Variable.get(prefect_name)
    except Exception:
        pass
    
    # Return default if nothing found
    return default


def get_connection_string(use_prefect_only: bool = False) -> str:
    """
    Build connection string from environment variables or Prefect Blocks/Variables.
    
    Args:
        use_prefect_only: If True, skip env vars and only use Prefect values
    
    Environment Variables (checked first, unless use_prefect_only=True):
        PGHOST - Database host (e.g., p.EXAMPLE.db.postgresbridge.com)
        PGPORT - Database port (default: 5432)
        PGDATABASE - Database name (e.g., postgres)
        PGUSER - Database user (e.g., application)
        PGPASSWORD - Database password
    
    Prefect Fallbacks (or primary if use_prefect_only=True):
        Secrets: pghost, pgpassword (sensitive values)
        Variables: pgport, pgdatabase, pguser (non-sensitive values)
    """
    # Get all connection parameters with env -> Prefect fallback
    host = get_env_or_prefect("PGHOST", "pghost", is_secret=True, use_prefect_only=use_prefect_only)
    port = get_env_or_prefect("PGPORT", "pgport", is_secret=False, default="5432", use_prefect_only=use_prefect_only)
    database = get_env_or_prefect("PGDATABASE", "pgdatabase", is_secret=False, use_prefect_only=use_prefect_only)
    user = get_env_or_prefect("PGUSER", "pguser", is_secret=False, use_prefect_only=use_prefect_only)
    password = get_env_or_prefect("PGPASSWORD", "pgpassword", is_secret=True, use_prefect_only=use_prefect_only)
    
    # Validate required parameters
    if not all([host, database, user, password]):
        missing = []
        if not host: missing.append("PGHOST / pghost")
        if not database: missing.append("PGDATABASE / pgdatabase")
        if not user: missing.append("PGUSER / pguser")
        if not password: missing.append("PGPASSWORD / pgpassword")
        raise ValueError(
            f"Missing required connection parameters: {', '.join(missing)}. "
            "Set these as environment variables in .env or as Prefect Blocks/Variables."
        )
    
    # Crunchy Bridge requires SSL
    return f"host={host} port={port} dbname={database} user={user} password={password} sslmode=require"


def get_connection(use_prefect_only: bool = False) -> Connection:
    """
    Get a connection to Crunchy Bridge PostgreSQL.
    
    Args:
        use_prefect_only: If True, skip env vars and only use Prefect values
    
    Returns:
        psycopg.Connection: Active database connection
        
    Example:
        >>> from crunchy_bridge_connection import get_connection
        >>> with get_connection() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT version()")
        ...         print(cur.fetchone())
    """
    conn_string = get_connection_string(use_prefect_only=use_prefect_only)
    return psycopg.connect(conn_string)


def test_connection(use_prefect_only: bool = False) -> bool:
    """Test the connection to Crunchy Bridge.
    
    Args:
        use_prefect_only: If True, skip env vars and only use Prefect values
    """
    source = "Prefect only" if use_prefect_only else "env vars -> Prefect fallback"
    print(f"Testing connection using: {source}")
    
    try:
        with get_connection(use_prefect_only=use_prefect_only) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                print(f"✓ Connected to Crunchy Bridge PostgreSQL")
                print(f"  Version: {version[:60]}...")
                return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    # ==========================================================================
    # CLI USAGE
    # ==========================================================================
    #
    # Test with env vars (default, falls back to Prefect):
    #   uv run -m crunchy_bridge_connection.connection
    #
    # Test with Prefect values only (skip env vars):
    #   uv run -m crunchy_bridge_connection.connection --prefect
    #
    # ==========================================================================
    
    import sys
    
    use_prefect_only = "--prefect" in sys.argv
    
    if use_prefect_only:
        print("Testing connection with Prefect values only...\n")
        print("Configuration sources: ALL FROM PREFECT")
    else:
        print("Testing connection with env vars -> Prefect fallback...\n")
        print("Configuration sources:")
        print(f"  PGHOST:     {'env' if os.getenv('PGHOST') else 'Prefect'}")
        print(f"  PGPORT:     {'env' if os.getenv('PGPORT') else 'Prefect/default'}")
        print(f"  PGDATABASE: {'env' if os.getenv('PGDATABASE') else 'Prefect'}")
        print(f"  PGUSER:     {'env' if os.getenv('PGUSER') else 'Prefect'}")
        print(f"  PGPASSWORD: {'env' if os.getenv('PGPASSWORD') else 'Prefect'}")
    
    print()
    test_connection(use_prefect_only=use_prefect_only)
