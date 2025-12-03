"""CSV and DataFrame loading utilities for Crunchy Bridge PostgreSQL."""

import csv
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd

from .connection import get_connection


def infer_column_types(csv_path: str, sample_rows: int = 100) -> dict[str, str]:
    """
    Infer PostgreSQL column types from CSV data.
    
    Args:
        csv_path: Path to CSV file
        sample_rows: Number of rows to sample for type inference
        
    Returns:
        Dict mapping column names to PostgreSQL types
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        
        # Track possible types for each column
        type_candidates = {col: {'int': True, 'float': True, 'bool': True} for col in columns}
        
        for i, row in enumerate(reader):
            if i >= sample_rows:
                break
                
            for col, value in row.items():
                if value is None or value.strip() == '':
                    continue
                    
                value = value.strip()
                
                # Check if it's a boolean
                if type_candidates[col]['bool']:
                    if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                        type_candidates[col]['bool'] = False
                
                # Check if it's an integer
                if type_candidates[col]['int']:
                    try:
                        int(value)
                    except ValueError:
                        type_candidates[col]['int'] = False
                
                # Check if it's a float
                if type_candidates[col]['float']:
                    try:
                        float(value)
                    except ValueError:
                        type_candidates[col]['float'] = False
    
    # Determine final types
    column_types = {}
    for col in columns:
        candidates = type_candidates[col]
        if candidates['bool']:
            column_types[col] = 'BOOLEAN'
        elif candidates['int']:
            column_types[col] = 'BIGINT'
        elif candidates['float']:
            column_types[col] = 'DOUBLE PRECISION'
        else:
            column_types[col] = 'TEXT'
    
    return column_types


def create_table_from_csv(
    csv_path: str,
    table_name: str,
    schema: str = "public",
    drop_existing: bool = False,
) -> str:
    """
    Create a PostgreSQL table based on CSV structure.
    
    Args:
        csv_path: Path to CSV file
        table_name: Name for the new table
        schema: Database schema (default: public)
        drop_existing: If True, drop existing table first
        
    Returns:
        The CREATE TABLE SQL statement used
    """
    column_types = infer_column_types(csv_path)
    
    # Sanitize column names for PostgreSQL
    def sanitize_name(name: str) -> str:
        # Replace spaces and special chars with underscores
        sanitized = ''.join(c if c.isalnum() else '_' for c in name)
        # Ensure it doesn't start with a number
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    columns_sql = []
    for col, pg_type in column_types.items():
        safe_col = sanitize_name(col)
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


def load_csv_to_table(
    csv_path: str,
    table_name: str,
    schema: str = "public",
    create_table: bool = True,
    drop_existing: bool = False,
    delimiter: str = ",",
) -> int:
    """
    Load a CSV file into a Crunchy Bridge PostgreSQL table.
    
    Args:
        csv_path: Path to the CSV file
        table_name: Target table name
        schema: Database schema (default: public)
        create_table: If True, create the table from CSV structure
        drop_existing: If True and create_table=True, drop existing table
        delimiter: CSV delimiter (default: comma)
        
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
        create_table_from_csv(str(csv_path), table_name, schema, drop_existing)
    
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
    with get_connection() as conn:
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
) -> None:
    """
    Ensure table exists with proper schema. Creates if not exists.
    
    Args:
        df: DataFrame to infer schema from
        table_name: Target table name
        schema: Database schema (default: public)
        primary_keys: List of column names for composite primary key
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
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Ensure schema exists
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            cur.execute(create_sql)
            conn.commit()
            print(f"✓ Ensured table {full_table_name} exists")


def upsert_dataframe_to_table(
    df: pd.DataFrame,
    table_name: str,
    primary_keys: list[str],
    schema: str = "public",
    create_table: bool = True,
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
        ensure_table_exists(df, table_name, schema, primary_keys)
    
    full_table_name = f'"{schema}"."{table_name}"'
    
    # Sanitize column names
    def sanitize_name(name: str) -> str:
        sanitized = ''.join(c if c.isalnum() else '_' for c in str(name))
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    # Get row count before upsert
    with get_connection() as conn:
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
    with get_connection() as conn:
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
) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a pandas DataFrame.
    
    Args:
        query: SQL query string
        params: Optional tuple of query parameters
        
    Returns:
        pd.DataFrame: Query results
        
    Example:
        >>> df = query_to_dataframe("SELECT * FROM eve_online.eve_market_data LIMIT 10")
        >>> print(df.head())
    """
    with get_connection() as conn:
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
) -> pd.DataFrame:
    """
    Pull data from a PostgreSQL table into a pandas DataFrame.
    
    Args:
        table_name: Name of the table to pull
        schema: Database schema (default: public)
        limit: Optional limit on number of rows
        where: Optional WHERE clause (without 'WHERE' keyword)
        
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
    
    df = query_to_dataframe(query)
    print(f"✓ Pulled {len(df):,} rows from {full_table_name}")
    
    return df


def pull_eve_market_data_from_db(
    limit: int | None = None,
    region_id: int | None = None,
    typeid: int | None = None,
) -> pd.DataFrame:
    """
    Pull EVE market data from Crunchy Bridge PostgreSQL.
    
    Args:
        limit: Optional limit on number of rows
        region_id: Optional filter by region ID
        typeid: Optional filter by item type ID
        
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
    )


if __name__ == "__main__":
    # =========================================================================
    # CLI USAGE (run as module with -m flag)
    # =========================================================================
    #
    # Pull EVE market data from Crunchy Bridge:
    # -----------------------------------------
    #   uv run -m crunchy_bridge_connection.csv_loader pull [--limit N] [--region REGION_ID] [--typeid TYPE_ID]
    #
    #   Examples:
    #     uv run -m crunchy_bridge_connection.csv_loader pull
    #     uv run -m crunchy_bridge_connection.csv_loader pull --limit 100
    #     uv run -m crunchy_bridge_connection.csv_loader pull --region 10000002
    #     uv run -m crunchy_bridge_connection.csv_loader pull --typeid 34 --limit 50
    #
    # Load CSV to table:
    # -----------------------------------------
    #   uv run -m crunchy_bridge_connection.csv_loader load <csv_file> <table_name> [--drop]
    #
    #   Examples:
    #     uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table
    #     uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --drop
    #
    # =========================================================================
    
    import sys
    
    def print_usage():
        print("Usage (run as module with -m flag):")
        print("  Pull data:  uv run -m crunchy_bridge_connection.csv_loader pull [--limit N] [--region ID] [--typeid ID]")
        print("  Load CSV:   uv run -m crunchy_bridge_connection.csv_loader load <csv_file> <table_name> [--drop]")
        print()
        print("Examples:")
        print("  uv run -m crunchy_bridge_connection.csv_loader pull --limit 10")
        print("  uv run -m crunchy_bridge_connection.csv_loader pull --region 10000002")
        print("  uv run -m crunchy_bridge_connection.csv_loader load data.csv my_table --drop")
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
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
            else:
                i += 1
        
        df = pull_eve_market_data_from_db(limit=limit, region_id=region_id, typeid=typeid)
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
        
        load_csv_to_table(csv_file, table_name, drop_existing=drop_existing)
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)

