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


def get_connection_string(
    use_prefect_only: bool = False,
    crunchy_or_snowflake: str = "crunchy",
) -> str:
    """
    Build connection string from environment variables or Prefect Blocks/Variables.
    
    Args:
        use_prefect_only: If True, skip env vars and only use Prefect values
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
    
    Crunchy Bridge Environment Variables (checked first, unless use_prefect_only=True):
        PGHOST - Database host (e.g., p.EXAMPLE.db.postgresbridge.com)
        PGPORT - Database port (default: 5432)
        PGDATABASE - Database name (e.g., postgres)
        PGUSER - Database user (e.g., application)
        PGPASSWORD - Database password
    
    Crunchy Bridge Prefect Fallbacks (or primary if use_prefect_only=True):
        Secrets: pghost, pgpassword (sensitive values)
        Variables: pgport, pgdatabase, pguser (non-sensitive values)
    
    Snowflake Environment Variables (checked first, unless use_prefect_only=True):
        SF_PGHOST - Database host
        SF_PGPORT - Database port (default: 5432)
        SF_PGDATABASE - Database name
        SF_PGUSER - Database user
        SF_PGPASSWORD - Database password
    
    Snowflake Prefect Fallbacks (or primary if use_prefect_only=True):
        Secrets: sf-pghost, sf-pgpassword (sensitive values)
        Variables: sf_pgport, sf_pgdatabase, sf_pguser (non-sensitive values)
    """
    if crunchy_or_snowflake not in ("crunchy", "snowflake"):
        raise ValueError(f"crunchy_or_snowflake must be 'crunchy' or 'snowflake', got '{crunchy_or_snowflake}'")
    
    if crunchy_or_snowflake == "crunchy":
        # Crunchy Bridge connection parameters
        host = get_env_or_prefect("PGHOST", "pghost", is_secret=True, use_prefect_only=use_prefect_only)
        port = get_env_or_prefect("PGPORT", "pgport", is_secret=False, default="5432", use_prefect_only=use_prefect_only)
        database = get_env_or_prefect("PGDATABASE", "pgdatabase", is_secret=False, use_prefect_only=use_prefect_only)
        user = get_env_or_prefect("PGUSER", "pguser", is_secret=False, use_prefect_only=use_prefect_only)
        password = get_env_or_prefect("PGPASSWORD", "pgpassword", is_secret=True, use_prefect_only=use_prefect_only)
    else:
        # Snowflake connection parameters
        host = get_env_or_prefect("SF_PGHOST", "sf-pghost", is_secret=True, use_prefect_only=use_prefect_only)
        port = get_env_or_prefect("SF_PGPORT", "sf_pgport", is_secret=False, default="5432", use_prefect_only=use_prefect_only)
        database = get_env_or_prefect("SF_PGDATABASE", "sf_pgdatabase", is_secret=False, use_prefect_only=use_prefect_only)
        user = get_env_or_prefect("SF_PGUSER", "sf_pguser", is_secret=False, use_prefect_only=use_prefect_only)
        password = get_env_or_prefect("SF_PGPASSWORD", "sf-pgpassword", is_secret=True, use_prefect_only=use_prefect_only)
    
    # Validate required parameters
    if not all([host, database, user, password]):
        missing = []
        if crunchy_or_snowflake == "crunchy":
            if not host: missing.append("PGHOST / pghost")
            if not database: missing.append("PGDATABASE / pgdatabase")
            if not user: missing.append("PGUSER / pguser")
            if not password: missing.append("PGPASSWORD / pgpassword")
        else:
            if not host: missing.append("SF_PGHOST / sf-pghost")
            if not database: missing.append("SF_PGDATABASE / sf_pgdatabase")
            if not user: missing.append("SF_PGUSER / sf_pguser")
            if not password: missing.append("SF_PGPASSWORD / sf-pgpassword")
        raise ValueError(
            f"Missing required connection parameters for {crunchy_or_snowflake}: {', '.join(missing)}. "
            "Set these as environment variables in .env or as Prefect Blocks/Variables."
        )
    
    # Both Crunchy Bridge and Snowflake require SSL
    return f"host={host} port={port} dbname={database} user={user} password={password} sslmode=require"


def get_connection(
    use_prefect_only: bool = False,
    crunchy_or_snowflake: str = "crunchy",
) -> Connection:
    """
    Get a connection to Crunchy Bridge or Snowflake PostgreSQL.
    
    Args:
        use_prefect_only: If True, skip env vars and only use Prefect values
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
    
    Returns:
        psycopg.Connection: Active database connection
        
    Example:
        >>> from crunchy_bridge_connection import get_connection
        >>> with get_connection() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT version()")
        ...         print(cur.fetchone())
        >>> # Connect to Snowflake PostgreSQL
        >>> with get_connection(crunchy_or_snowflake="snowflake") as conn:
        ...     pass
    """
    conn_string = get_connection_string(
        use_prefect_only=use_prefect_only,
        crunchy_or_snowflake=crunchy_or_snowflake,
    )
    return psycopg.connect(conn_string)


def test_connection(
    use_prefect_only: bool = False,
    crunchy_or_snowflake: str = "crunchy",
) -> bool:
    """Test the connection to Crunchy Bridge or Snowflake PostgreSQL.
    
    Args:
        use_prefect_only: If True, skip env vars and only use Prefect values
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
    """
    source = "Prefect only" if use_prefect_only else "env vars -> Prefect fallback"
    db_name = "Crunchy Bridge" if crunchy_or_snowflake == "crunchy" else "Snowflake"
    print(f"Testing {db_name} connection using: {source}")
    
    try:
        with get_connection(
            use_prefect_only=use_prefect_only,
            crunchy_or_snowflake=crunchy_or_snowflake,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                print(f"✓ Connected to {db_name} PostgreSQL")
                print(f"  Version: {version[:60]}...")
                
                # List all tables in the database
                cur.execute("""
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_type = 'BASE TABLE' 
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name
                """)
                tables = cur.fetchall()
                
                if tables:
                    print(f"\n  Tables ({len(tables)} found):")
                    for schema, table in tables:
                        print(f"    {schema}.{table}")
                else:
                    print("\n  No user tables found.")
                
                return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    # ==========================================================================
    # CLI USAGE
    # ==========================================================================
    #
    # Test Crunchy Bridge with env vars (default, falls back to Prefect):
    #   uv run -m crunchy_bridge_connection.connection
    #
    # Test Crunchy Bridge with Prefect values only (skip env vars):
    #   uv run -m crunchy_bridge_connection.connection --prefect
    #
    # Test Snowflake PostgreSQL with env vars (falls back to Prefect):
    #   uv run -m crunchy_bridge_connection.connection --snowflake
    #
    # Test Snowflake PostgreSQL with Prefect values only:
    #   uv run -m crunchy_bridge_connection.connection --snowflake --prefect
    #
    # ==========================================================================
    
    import sys
    
    use_prefect_only = "--prefect" in sys.argv
    use_snowflake = "--snowflake" in sys.argv
    crunchy_or_snowflake = "snowflake" if use_snowflake else "crunchy"
    db_name = "Snowflake" if use_snowflake else "Crunchy Bridge"
    
    if use_prefect_only:
        print(f"Testing {db_name} connection with Prefect values only...\n")
        print("Configuration sources: ALL FROM PREFECT")
    else:
        print(f"Testing {db_name} connection with env vars -> Prefect fallback...\n")
        print("Configuration sources:")
        if use_snowflake:
            print(f"  SF_PGHOST:     {'env' if os.getenv('SF_PGHOST') else 'Prefect'}")
            print(f"  SF_PGPORT:     {'env' if os.getenv('SF_PGPORT') else 'Prefect/default'}")
            print(f"  SF_PGDATABASE: {'env' if os.getenv('SF_PGDATABASE') else 'Prefect'}")
            print(f"  SF_PGUSER:     {'env' if os.getenv('SF_PGUSER') else 'Prefect'}")
            print(f"  SF_PGPASSWORD: {'env' if os.getenv('SF_PGPASSWORD') else 'Prefect'}")
        else:
            print(f"  PGHOST:     {'env' if os.getenv('PGHOST') else 'Prefect'}")
            print(f"  PGPORT:     {'env' if os.getenv('PGPORT') else 'Prefect/default'}")
            print(f"  PGDATABASE: {'env' if os.getenv('PGDATABASE') else 'Prefect'}")
            print(f"  PGUSER:     {'env' if os.getenv('PGUSER') else 'Prefect'}")
            print(f"  PGPASSWORD: {'env' if os.getenv('PGPASSWORD') else 'Prefect'}")
    
    print()
    test_connection(use_prefect_only=use_prefect_only, crunchy_or_snowflake=crunchy_or_snowflake)
