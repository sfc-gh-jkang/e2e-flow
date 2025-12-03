"""Crunchy Bridge PostgreSQL connection management.

    This module provides utilities for connecting to Crunchy Bridge PostgreSQL.
    It uses the psycopg library to connect to the database and provides a connection string and a function to get a connection.
    It also provides a function to test the connection.

    To test this module run: uv run crunchy_bridge_connection/connection.py
"""

import os

import psycopg
from dotenv import load_dotenv
from psycopg import Connection

# Auto-load .env file if present
load_dotenv()

# Define schema names
postgres_schema = "eve_online"
# Define table names
eve_market_data_table = "eve_market_data"


def get_connection_string() -> str:
    """
    Build connection string from environment variables.
    
    Uses standard PostgreSQL environment variables:
        PGHOST - Database host (e.g., p.EXAMPLE.db.postgresbridge.com)
        PGPORT - Database port (default: 5432)
        PGDATABASE - Database name (e.g., postgres)
        PGUSER - Database user (e.g., application)
        PGPASSWORD - Database password
    
    These are the standard libpq environment variables that psycopg
    natively supports.
    """
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    
    if not all([host, database, user, password]):
        missing = []
        if not host: missing.append("PGHOST")
        if not database: missing.append("PGDATABASE")
        if not user: missing.append("PGUSER")
        if not password: missing.append("PGPASSWORD")
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set these in your .env file."
        )
    
    # Crunchy Bridge requires SSL
    return f"host={host} port={port} dbname={database} user={user} password={password} sslmode=require"


def get_connection() -> Connection:
    """
    Get a connection to Crunchy Bridge PostgreSQL.
    
    Returns:
        psycopg.Connection: Active database connection
        
    Example:
        >>> from crunchy_bridge_connection import get_connection
        >>> with get_connection() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT version()")
        ...         print(cur.fetchone())
    """
    conn_string = get_connection_string()
    return psycopg.connect(conn_string)


def test_connection() -> bool:
    """Test the connection to Crunchy Bridge."""
    try:
        with get_connection() as conn:
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
    test_connection()
