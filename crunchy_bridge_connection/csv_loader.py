"""CSV and DataFrame loading utilities for Crunchy Bridge PostgreSQL."""

import csv
from io import StringIO
from pathlib import Path

import pandas as pd

from .connection import get_connection


def create_table_from_csv(
    csv_path: str,
    table_name: str,
    schema: str = "public",
    drop_existing: bool = False,
    primary_keys: list[str] | None = None,
    crunchy_or_snowflake: str = "crunchy",
) -> str:
    """
    Create a PostgreSQL table based on CSV structure.
    
    This is a convenience wrapper that loads a CSV into a DataFrame and then
    calls ensure_table_exists() to create the table.
    
    Args:
        csv_path: Path to CSV file
        table_name: Name for the new table
        schema: Database schema (default: public)
        drop_existing: If True, drop existing table first (DESTRUCTIVE!)
        primary_keys: List of column names for composite primary key
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
        
    Returns:
        The CREATE TABLE SQL statement used
    """
    # Load CSV into DataFrame to infer types via pandas
    df = pd.read_csv(csv_path)
    
    # Use the core ensure_table_exists function
    return ensure_table_exists(
        df=df,
        table_name=table_name,
        schema=schema,
        primary_keys=primary_keys,
        drop_existing=drop_existing,
        crunchy_or_snowflake=crunchy_or_snowflake,
    )


def load_csv_to_table(
    csv_path: str,
    table_name: str,
    schema: str = "public",
    create_table: bool = True,
    drop_existing: bool = False,
    delimiter: str = ",",
    primary_keys: list[str] | None = None,
    crunchy_or_snowflake: str = "crunchy",
) -> int:
    """
    Load a CSV file into a Crunchy Bridge or Snowflake PostgreSQL table.
    
    Args:
        csv_path: Path to the CSV file
        table_name: Target table name
        schema: Database schema (default: public)
        create_table: If True, create the table from CSV structure
        drop_existing: If True and create_table=True, drop existing table (DESTRUCTIVE!)
        delimiter: CSV delimiter (default: comma)
        primary_keys: List of column names for composite primary key
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
        
    Returns:
        Number of rows loaded
        
    Example:
        >>> from crunchy_bridge_connection import load_csv_to_table
        >>> rows = load_csv_to_table(
        ...     "eve_online_data/eve_market_all_a4e_regions_20251203_135659.csv",
        ...     "eve_market_data",
        ...     drop_existing=True
        ... )
        >>> print(f"Loaded {rows} rows")
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Create table if requested
    if create_table:
        create_table_from_csv(
            csv_path=str(csv_path),
            table_name=table_name,
            schema=schema,
            drop_existing=drop_existing,
            primary_keys=primary_keys,
            crunchy_or_snowflake=crunchy_or_snowflake,
        )
    
    full_table_name = f'"{schema}"."{table_name}"'
    
    # Get column names from CSV (sanitized)
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
    
    def sanitize_name(name: str) -> str:
        sanitized = ''.join(c if c.isalnum() else '_' for c in name)
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    columns = [f'"{sanitize_name(h)}"' for h in headers]
    columns_str = ', '.join(columns)
    
    # Load data using COPY
    copy_sql = f"COPY {full_table_name} ({columns_str}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER '{delimiter}')"
    
    rows_loaded = 0
    with get_connection(crunchy_or_snowflake=crunchy_or_snowflake) as conn:
        with conn.cursor() as cur:
            with open(csv_path, 'r', encoding='utf-8') as f:
                with cur.copy(copy_sql) as copy:
                    while data := f.read(65536):  # 64KB chunks
                        copy.write(data)
            
            # Get row count
            cur.execute(f"SELECT COUNT(*) FROM {full_table_name}")
            rows_loaded = cur.fetchone()[0]
            
            conn.commit()
    
    print(f"✓ Loaded {rows_loaded:,} rows into {full_table_name}")
    return rows_loaded


def pandas_dtype_to_postgres(dtype) -> str:
    """Convert pandas dtype to PostgreSQL type.
    
    Args:
        dtype: pandas dtype object
        
    Returns:
        PostgreSQL type string
    """
    dtype_str = str(dtype).lower()
    
    if 'int' in dtype_str:
        return 'BIGINT'
    elif 'float' in dtype_str:
        return 'DOUBLE PRECISION'
    elif 'bool' in dtype_str:
        return 'BOOLEAN'
    elif 'datetime' in dtype_str:
        return 'TIMESTAMP'
    elif 'date' in dtype_str:
        return 'DATE'
    elif 'timedelta' in dtype_str:
        return 'INTERVAL'
    else:
        return 'TEXT'


def create_table_from_dataframe(
    df: pd.DataFrame,
    table_name: str,
    schema: str = "public",
    drop_existing: bool = False,
) -> str:
    """
    Create a PostgreSQL table based on DataFrame structure.
    
    Args:
        df: pandas DataFrame
        table_name: Name for the new table
        schema: Database schema (default: public)
        drop_existing: If True, drop existing table first
        
    Returns:
        The CREATE TABLE SQL statement used
    """
    def sanitize_name(name: str) -> str:
        sanitized = ''.join(c if c.isalnum() else '_' for c in str(name))
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    columns_sql = []
    for col in df.columns:
        safe_col = sanitize_name(col)
        pg_type = pandas_dtype_to_postgres(df[col].dtype)
        columns_sql.append(f'    "{safe_col}" {pg_type}')
    
    full_table_name = f'"{schema}"."{table_name}"'
    
    create_sql = f"""CREATE TABLE {full_table_name} (
{',\n'.join(columns_sql)}
);"""
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            if drop_existing:
                cur.execute(f"DROP TABLE IF EXISTS {full_table_name} CASCADE")
                print(f"Dropped existing table {full_table_name}")
            
            cur.execute(create_sql)
            conn.commit()
            print(f"✓ Created table {full_table_name}")
    
    return create_sql


def load_dataframe_to_table(
    df: pd.DataFrame,
    table_name: str,
    schema: str = "public",
    create_table: bool = True,
    drop_existing: bool = False,
) -> int:
    """
    Load a pandas DataFrame into a Crunchy Bridge PostgreSQL table.
    
    Uses PostgreSQL COPY protocol for fast bulk loading.
    Handles NaT/NaN values by converting them to NULL.
    
    Args:
        df: pandas DataFrame to load
        table_name: Target table name
        schema: Database schema (default: public)
        create_table: If True, create the table from DataFrame structure
        drop_existing: If True and create_table=True, drop existing table
        
    Returns:
        Number of rows loaded
        
    Example:
        >>> from crunchy_bridge_connection import load_dataframe_to_table
        >>> import pandas as pd
        >>> df = pd.read_csv("data.csv")
        >>> rows = load_dataframe_to_table(df, "my_table", drop_existing=True)
        >>> print(f"Loaded {rows} rows")
    """
    if df.empty:
        print("⚠ DataFrame is empty, nothing to load")
        return 0
    
    # Create table if requested
    if create_table:
        create_table_from_dataframe(df, table_name, schema, drop_existing)
    
    full_table_name = f'"{schema}"."{table_name}"'
    
    # Sanitize column names
    def sanitize_name(name: str) -> str:
        sanitized = ''.join(c if c.isalnum() else '_' for c in str(name))
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    columns = [f'"{sanitize_name(col)}"' for col in df.columns]
    columns_str = ', '.join(columns)
    
    # Convert DataFrame to CSV in memory
    # Use na_rep='' to convert NaN/NaT to empty string (NULL in COPY)
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep='')
    buffer.seek(0)
    
    # Load using COPY protocol
    copy_sql = f"COPY {full_table_name} ({columns_str}) FROM STDIN WITH (FORMAT csv, NULL '')"
    
    rows_loaded = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            with cur.copy(copy_sql) as copy:
                copy.write(buffer.getvalue())
            
            # Get row count
            cur.execute(f"SELECT COUNT(*) FROM {full_table_name}")
            rows_loaded = cur.fetchone()[0]
            
            conn.commit()
    
    print(f"✓ Loaded {rows_loaded:,} rows into {full_table_name}")
    return rows_loaded


def ensure_table_exists(
    df: pd.DataFrame,
    table_name: str,
    schema: str = "public",
    primary_keys: list[str] | None = None,
    drop_existing: bool = False,
    crunchy_or_snowflake: str = "crunchy",
) -> str:
    """
    Ensure table exists with proper schema. Creates if not exists.
    
    This is the core table creation function used by both CSV loading and
    DataFrame upsert operations.
    
    Args:
        df: DataFrame to infer schema from
        table_name: Target table name
        schema: Database schema (default: public)
        primary_keys: List of column names for composite primary key
        drop_existing: If True, drop existing table first (DESTRUCTIVE!)
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
            
    Returns:
        The CREATE TABLE SQL statement used
    """
    def sanitize_name(name: str) -> str:
        sanitized = ''.join(c if c.isalnum() else '_' for c in str(name))
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    columns_sql = []
    for col in df.columns:
        safe_col = sanitize_name(col)
        pg_type = pandas_dtype_to_postgres(df[col].dtype)
        columns_sql.append(f'    "{safe_col}" {pg_type}')
    
    # Add primary key constraint if specified
    pk_clause = ""
    if primary_keys:
        pk_cols = ', '.join([f'"{sanitize_name(pk)}"' for pk in primary_keys])
        pk_clause = f",\n    PRIMARY KEY ({pk_cols})"
    
    full_table_name = f'"{schema}"."{table_name}"'
    
    create_sql = f"""CREATE TABLE IF NOT EXISTS {full_table_name} (
{',\n'.join(columns_sql)}{pk_clause}
);"""
    
    with get_connection(crunchy_or_snowflake=crunchy_or_snowflake) as conn:
        with conn.cursor() as cur:
            # Ensure schema exists
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            
            if drop_existing:
                cur.execute(f"DROP TABLE IF EXISTS {full_table_name} CASCADE")
                print(f"Dropped existing table {full_table_name}")
            
            cur.execute(create_sql)
            conn.commit()
            print(f"✓ Ensured table {full_table_name} exists")
    
    return create_sql


def upsert_dataframe_to_table(
    df: pd.DataFrame,
    table_name: str,
    primary_keys: list[str],
    schema: str = "public",
    create_table: bool = True,
    drop_existing: bool = False,
    crunchy_or_snowflake: str = "crunchy",
) -> dict[str, int]:
    """
    Upsert (INSERT ON CONFLICT UPDATE) a DataFrame into PostgreSQL.
    
    Uses PostgreSQL's INSERT ... ON CONFLICT DO UPDATE for efficient merging.
    Handles NaT/NaN values by converting them to NULL.
    
    Args:
        df: pandas DataFrame to upsert
        table_name: Target table name
        primary_keys: List of column names that form the composite primary key
        schema: Database schema (default: public)
        create_table: If True, create table if it doesn't exist
        drop_existing: If True, drop existing table first (useful to recreate with correct PK)
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
        
    Returns:
        Dict with 'inserted' and 'updated' counts (approximate)
        
    Example:
        >>> from crunchy_bridge_connection import upsert_dataframe_to_table
        >>> result = upsert_dataframe_to_table(
        ...     df,
        ...     "eve_market_data",
        ...     primary_keys=["region_id", "typeid", "last_data"],
        ...     schema="eve_online"
        ... )
        >>> print(f"Inserted: {result['inserted']}, Updated: {result['updated']}")
    """
    if df.empty:
        print("⚠ DataFrame is empty, nothing to upsert")
        return {'inserted': 0, 'updated': 0}
    
    if not primary_keys:
        raise ValueError("primary_keys must be specified for upsert operation")
    
    # Create table if requested
    if create_table:
        ensure_table_exists(
            df=df,
            table_name=table_name,
            schema=schema,
            primary_keys=primary_keys,
            drop_existing=drop_existing,
            crunchy_or_snowflake=crunchy_or_snowflake,
        )
    
    full_table_name = f'"{schema}"."{table_name}"'
    
    # Sanitize column names
    def sanitize_name(name: str) -> str:
        sanitized = ''.join(c if c.isalnum() else '_' for c in str(name))
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    # Get row count before upsert
    with get_connection(crunchy_or_snowflake=crunchy_or_snowflake) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {full_table_name}")
            count_before = cur.fetchone()[0]
    
    # Prepare column lists
    all_columns = [sanitize_name(col) for col in df.columns]
    pk_columns = [sanitize_name(pk) for pk in primary_keys]
    update_columns = [col for col in all_columns if col not in pk_columns]
    
    # Build INSERT ... ON CONFLICT DO UPDATE statement
    columns_str = ', '.join([f'"{col}"' for col in all_columns])
    placeholders = ', '.join(['%s'] * len(all_columns))
    
    conflict_cols = ', '.join([f'"{col}"' for col in pk_columns])
    update_set = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in update_columns])
    
    upsert_sql = f"""
        INSERT INTO {full_table_name} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}
    """
    
    # Convert DataFrame to list of tuples, handling NaN/NaT
    def convert_value(val):
        if pd.isna(val):
            return None
        return val
    
    rows = [tuple(convert_value(val) for val in row) for row in df.values]
    
    # Execute upsert in batches
    batch_size = 1000
    with get_connection(crunchy_or_snowflake=crunchy_or_snowflake) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                cur.executemany(upsert_sql, batch)
            conn.commit()
        
        # Get row count after upsert
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {full_table_name}")
            count_after = cur.fetchone()[0]
    
    inserted = count_after - count_before
    updated = len(df) - inserted
    
    print(f"✓ Upserted {len(df):,} rows into {full_table_name}")
    print(f"  → Inserted: {inserted:,}, Updated: {updated:,}")
    
    return {'inserted': inserted, 'updated': updated}


def query_to_dataframe(
    query: str,
    params: tuple | None = None,
    crunchy_or_snowflake: str = "crunchy",
) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a pandas DataFrame.
    
    Args:
        query: SQL query string
        params: Optional tuple of query parameters
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
        
    Returns:
        pd.DataFrame: Query results
        
    Example:
        >>> df = query_to_dataframe("SELECT * FROM eve_online.eve_market_data LIMIT 10")
        >>> print(df.head())
    """
    with get_connection(crunchy_or_snowflake=crunchy_or_snowflake) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    
    return pd.DataFrame(rows, columns=columns)


def pull_table_to_dataframe(
    table_name: str,
    schema: str = "public",
    limit: int | None = None,
    where: str | None = None,
    crunchy_or_snowflake: str = "crunchy",
) -> pd.DataFrame:
    """
    Pull data from a PostgreSQL table into a pandas DataFrame.
    
    Args:
        table_name: Name of the table to pull
        schema: Database schema (default: public)
        limit: Optional limit on number of rows
        where: Optional WHERE clause (without 'WHERE' keyword)
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
        
    Returns:
        pd.DataFrame: Table data
        
    Example:
        >>> from crunchy_bridge_connection import pull_table_to_dataframe
        >>> df = pull_table_to_dataframe("eve_market_data", schema="eve_online", limit=100)
        >>> print(df.head())
    """
    full_table_name = f'"{schema}"."{table_name}"'
    
    query = f"SELECT * FROM {full_table_name}"
    
    if where:
        query += f" WHERE {where}"
    
    if limit:
        query += f" LIMIT {limit}"
    
    df = query_to_dataframe(query, crunchy_or_snowflake=crunchy_or_snowflake)
    print(f"✓ Pulled {len(df):,} rows from {full_table_name}")
    
    return df


def pull_eve_market_data_from_db(
    limit: int | None = None,
    region_id: int | None = None,
    typeid: int | None = None,
    crunchy_or_snowflake: str = "crunchy",
) -> pd.DataFrame:
    """
    Pull EVE market data from Crunchy Bridge or Snowflake PostgreSQL.
    
    Args:
        limit: Optional limit on number of rows
        region_id: Optional filter by region ID
        typeid: Optional filter by item type ID
        crunchy_or_snowflake: Which database to connect to. Options: "crunchy" or "snowflake".
            Default is "crunchy".
        
    Returns:
        pd.DataFrame: EVE market data
        
    Example:
        >>> from crunchy_bridge_connection import pull_eve_market_data_from_db
        >>> # Get all data (limited to 1000 rows)
        >>> df = pull_eve_market_data_from_db(limit=1000)
        >>> # Get data for The Forge region only
        >>> df = pull_eve_market_data_from_db(region_id=10000002)
        >>> # Get data for a specific item
        >>> df = pull_eve_market_data_from_db(typeid=34)
        >>> # Get data from Snowflake
        >>> df = pull_eve_market_data_from_db(limit=100, crunchy_or_snowflake="snowflake")
    """
    from .connection import postgres_schema, eve_market_data_table
    
    # Build WHERE clause
    conditions = []
    if region_id:
        conditions.append(f"region_id = {region_id}")
    if typeid:
        conditions.append(f"typeid = {typeid}")
    
    where = " AND ".join(conditions) if conditions else None
    
    return pull_table_to_dataframe(
        table_name=eve_market_data_table,
        schema=postgres_schema,
        limit=limit,
        where=where,
        crunchy_or_snowflake=crunchy_or_snowflake,
    )


if __name__ == "__main__":
    # =========================================================================
    # CLI USAGE (run as module with -m flag)
    # =========================================================================
    #
    # Pull EVE market data from Crunchy Bridge or Snowflake:
    # -----------------------------------------
    #   uv run -m crunchy_bridge_connection.csv_loader pull [--limit N] [--region REGION_ID] [--typeid TYPE_ID] [--snowflake]
    #
    #   Examples:
    #     uv run -m crunchy_bridge_connection.csv_loader pull
    #     uv run -m crunchy_bridge_connection.csv_loader pull --limit 100
    #     uv run -m crunchy_bridge_connection.csv_loader pull --region 10000002
    #     uv run -m crunchy_bridge_connection.csv_loader pull --typeid 34 --limit 50
    #     uv run -m crunchy_bridge_connection.csv_loader pull --snowflake --limit 100
    #
    # Load CSV to table (APPEND - fast bulk insert, NO primary key):
    # -----------------------------------------
    #   uv run -m crunchy_bridge_connection.csv_loader load <csv_file> <table_name> [--schema SCHEMA] [--drop] [--snowflake]
    #
    #   ⚠️  NOTE: 'load' creates tables WITHOUT primary keys. Use for:
    #       - Initial bulk loads when you know data is unique
    #       - Log/event tables that don't need deduplication
    #       - Fast loading when you'll run 'upsert --drop' afterward
    #
    #   Examples:
    #     uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table
    #     uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --schema eve_online
    #     uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --snowflake
    #     uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --schema eve_online --snowflake --drop
    #
    # Upsert CSV to table (MERGE - deduplicates on primary keys):
    # -----------------------------------------
    #   uv run -m crunchy_bridge_connection.csv_loader upsert <csv_file> <table_name> --primary-keys KEY1,KEY2 [--schema SCHEMA] [--drop] [--snowflake]
    #
    #   ⚠️  NOTE: 'upsert' creates tables WITH primary key constraint.
    #       - If table was created by 'load' (no PK), you MUST use --drop first
    #       - After first run with --drop, future upserts work without --drop
    #
    #   📋 HOW TO DETERMINE PRIMARY KEYS:
    #       Primary keys are the columns that uniquely identify each row in your data.
    #       For EVE market data, the composite key is:
    #         - region_id: EVE region (e.g., The Forge = 10000002)
    #         - typeid: Item type ID (e.g., Tritanium = 34)
    #         - last_data: Date of market snapshot
    #       Together: each item in each region has one entry per day.
    #       These are defined in prefect_test.py as EVE_MARKET_PRIMARY_KEYS.
    #
    #   Examples:
    #     uv run -m crunchy_bridge_connection.csv_loader upsert data.csv my_table --primary-keys id
    #     uv run -m crunchy_bridge_connection.csv_loader upsert data.csv eve_market_data --primary-keys region_id,typeid,last_data --schema eve_online
    #     uv run -m crunchy_bridge_connection.csv_loader upsert data.csv eve_market_data --primary-keys region_id,typeid,last_data --schema eve_online --snowflake
    #     # First time after using 'load', use --drop to recreate with PK:
    #     uv run -m crunchy_bridge_connection.csv_loader upsert data.csv eve_market_data --primary-keys region_id,typeid,last_data --schema eve_online --snowflake --drop
    #
    # ⚠️  WARNING: --drop is DESTRUCTIVE!
    # -----------------------------------------
    #   The --drop flag will PERMANENTLY DELETE the existing table and ALL
    #   its data before creating a new one. USE WITH CAUTION!
    #
    # =========================================================================
    
    import sys
    
    def print_usage():
        print("Usage (run as module with -m flag):")
        print("  Pull data:   uv run -m crunchy_bridge_connection.csv_loader pull [--limit N] [--region ID] [--typeid ID] [--snowflake]")
        print("  Load CSV:    uv run -m crunchy_bridge_connection.csv_loader load <csv_file> <table_name> [--schema SCHEMA] [--drop] [--snowflake]")
        print("  Upsert CSV:  uv run -m crunchy_bridge_connection.csv_loader upsert <csv_file> <table_name> --primary-keys KEY1,KEY2 [--schema SCHEMA] [--drop] [--snowflake]")
        print()
        print("Commands:")
        print("  pull    - Pull data from database to display")
        print("  load    - Bulk append CSV to table (fast COPY, NO primary key created)")
        print("  upsert  - Merge CSV to table (creates PRIMARY KEY, deduplicates on PK)")
        print()
        print("Options:")
        print("  --schema SCHEMA          Target database schema (default: public)")
        print("  --primary-keys KEY1,KEY2 Comma-separated primary key columns (required for upsert)")
        print("  --snowflake              Use Snowflake PostgreSQL instead of Crunchy Bridge (default: Crunchy)")
        print("  --drop                   Drop existing table before loading (recreates with proper PK for upsert)")
        print()
        print("  " + "=" * 70)
        print("  ⚠️  WARNING: --drop is DESTRUCTIVE! It will permanently DELETE the")
        print("  existing table and ALL its data before creating a new one.")
        print("  USE WITH CAUTION - there is NO confirmation prompt!")
        print("  " + "=" * 70)
        print()
        print("  " + "-" * 70)
        print("  📋 NOTE: 'load' creates tables WITHOUT primary keys.")
        print("     If you used 'load' first and now want to 'upsert', you MUST use")
        print("     --drop on the first upsert to recreate the table with a PK.")
        print("  " + "-" * 70)
        print()
        print("Examples:")
        print("  # Pull data")
        print("  uv run -m crunchy_bridge_connection.csv_loader pull --limit 10")
        print("  uv run -m crunchy_bridge_connection.csv_loader pull --snowflake --limit 50")
        print()
        print("  # Load (append) - fast bulk insert, NO primary key")
        print("  uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --drop")
        print("  uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --schema eve_online --snowflake")
        print()
        print("  # Upsert (merge) - creates table WITH primary key, deduplicates")
        print("  # First time (or after 'load'), use --drop to create PK:")
        print("  uv run -m crunchy_bridge_connection.csv_loader upsert data.csv eve_market_data --primary-keys region_id,typeid,last_data --schema eve_online --drop")
        print("  # Future runs - no --drop needed:")
        print("  uv run -m crunchy_bridge_connection.csv_loader upsert data.csv eve_market_data --primary-keys region_id,typeid,last_data --schema eve_online --snowflake")
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Parse global --snowflake flag
    use_snowflake = "--snowflake" in sys.argv
    crunchy_or_snowflake = "snowflake" if use_snowflake else "crunchy"
    db_name = "Snowflake" if use_snowflake else "Crunchy Bridge"
    
    if command == "pull":
        # Parse optional arguments
        limit = None
        region_id = None
        typeid = None
        
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--region" and i + 1 < len(sys.argv):
                region_id = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--typeid" and i + 1 < len(sys.argv):
                typeid = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--snowflake":
                i += 1  # Already parsed above
            else:
                i += 1
        
        print(f"Pulling data from {db_name}...")
        df = pull_eve_market_data_from_db(
            limit=limit,
            region_id=region_id,
            typeid=typeid,
            crunchy_or_snowflake=crunchy_or_snowflake,
        )
        print(f"\nData shape: {df.shape}")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst 10 rows:\n{df.head(10)}")
        
    elif command == "load":
        if len(sys.argv) < 4:
            print("Error: load requires <csv_file> and <table_name>")
            print_usage()
            sys.exit(1)
        
        csv_file = sys.argv[2]
        table_name = sys.argv[3]
        drop_existing = "--drop" in sys.argv
        
        # Parse --schema argument
        schema = "public"
        for i, arg in enumerate(sys.argv):
            if arg == "--schema" and i + 1 < len(sys.argv):
                schema = sys.argv[i + 1]
                break
        
        # Show warning if --drop is used
        if drop_existing:
            print()
            print("=" * 70)
            print("⚠️  WARNING: --drop flag detected!")
            print(f"   This will PERMANENTLY DELETE table: {schema}.{table_name}")
            print("   All existing data in this table will be LOST!")
            print("=" * 70)
            print()
        
        print(f"Loading data to {db_name} ({schema}.{table_name})...")
        load_csv_to_table(
            csv_file,
            table_name,
            schema=schema,
            drop_existing=drop_existing,
            crunchy_or_snowflake=crunchy_or_snowflake,
        )
    
    elif command == "upsert":
        if len(sys.argv) < 4:
            print("Error: upsert requires <csv_file> and <table_name>")
            print_usage()
            sys.exit(1)
        
        csv_file = sys.argv[2]
        table_name = sys.argv[3]
        drop_existing = "--drop" in sys.argv
        
        # Parse --schema argument
        schema = "public"
        for i, arg in enumerate(sys.argv):
            if arg == "--schema" and i + 1 < len(sys.argv):
                schema = sys.argv[i + 1]
                break
        
        # Parse --primary-keys argument (required for upsert)
        primary_keys = None
        for i, arg in enumerate(sys.argv):
            if arg == "--primary-keys" and i + 1 < len(sys.argv):
                primary_keys = [k.strip() for k in sys.argv[i + 1].split(",")]
                break
        
        if not primary_keys:
            print("Error: upsert requires --primary-keys argument")
            print("Example: --primary-keys region_id,typeid,last_data")
            print_usage()
            sys.exit(1)
        
        # Check if CSV file exists
        from pathlib import Path
        if not Path(csv_file).exists():
            print(f"Error: CSV file not found: {csv_file}")
            sys.exit(1)
        
        # Show warning if --drop is used
        if drop_existing:
            print()
            print("=" * 70)
            print("⚠️  WARNING: --drop flag detected!")
            print(f"   This will PERMANENTLY DELETE table: {schema}.{table_name}")
            print("   All existing data in this table will be LOST!")
            print("   Table will be recreated with PRIMARY KEY constraint.")
            print("=" * 70)
            print()
        
        print(f"Upserting data to {db_name} ({schema}.{table_name})...")
        print(f"  Primary keys: {primary_keys}")
        
        # Load CSV into DataFrame
        df = pd.read_csv(csv_file)
        print(f"  Loaded {len(df):,} rows from CSV")
        
        # Upsert to database
        result = upsert_dataframe_to_table(
            df=df,
            table_name=table_name,
            primary_keys=primary_keys,
            schema=schema,
            create_table=True,
            drop_existing=drop_existing,
            crunchy_or_snowflake=crunchy_or_snowflake,
        )
        
        print(f"\n✓ Upsert complete!")
        print(f"  Inserted: {result['inserted']:,}")
        print(f"  Updated: {result['updated']:,}")
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)

