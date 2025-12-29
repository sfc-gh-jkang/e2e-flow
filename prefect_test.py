"""Prefect flows for EVE Online market data ETL pipeline."""

from prefect import flow, task

from eve_online_data.eve_market_pull import (
    pull_eve_market_data,
    read_eve_market_data_from_csv,
)
from crunchy_bridge_connection import (
    upsert_dataframe_to_table,
    postgres_schema,
    eve_market_data_table,
)


# Define the merge keys for EVE market data
# Each item (typeid) in each region has one market data entry per day (last_data)
EVE_MARKET_PRIMARY_KEYS = ["region_id", "typeid", "last_data"]


@task
def pull_market_data() -> str:
    """Pull EVE market data from API and save to CSV."""
    csv_file = pull_eve_market_data()
    print(f"✓ Pulled market data to: {csv_file}")
    return csv_file


@task
def validate_and_load_csv(csv_file: str):
    """Load CSV and validate with pandera schema."""
    df = read_eve_market_data_from_csv(csv_file)
    print(f"✓ Loaded and validated {len(df):,} rows from CSV")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Data types:\n{df.dtypes}")
    return df


@task
def upsert_to_postgres(
    df,
    table_name: str,
    schema: str,
    primary_keys: list[str],
    crunchy_or_snowflake: str = "crunchy",
):
    """Upsert DataFrame to PostgreSQL (merge on primary keys).
    
    Args:
        df: pandas DataFrame to upsert
        table_name: Target table name
        schema: Database schema
        primary_keys: List of columns forming the composite primary key
        crunchy_or_snowflake: Target database - "crunchy" or "snowflake"
    """
    result = upsert_dataframe_to_table(
        df=df,
        table_name=table_name,
        primary_keys=primary_keys,
        schema=schema,
        create_table=True,  # Creates table with PK if not exists
        crunchy_or_snowflake=crunchy_or_snowflake,
    )
    return result


@flow(log_prints=True)
def load_eve_market_data(
    csv_file: str | None = None,
    crunchy_or_snowflake: str = "crunchy",
):
    """
    ETL flow for EVE Online market data.
    
    1. Pull market data from API (or use provided CSV)
    2. Load and validate CSV with pandera
    3. Create PostgreSQL table if not exists (with primary key)
    4. Upsert (merge) data into PostgreSQL (Crunchy Bridge or Snowflake)
    
    Args:
        csv_file: Optional path to existing CSV file. If None, pulls fresh data.
        crunchy_or_snowflake: Target database - "crunchy" (default) or "snowflake"
        
    Merge Keys:
        - region_id: The EVE region (e.g., The Forge, Domain)
        - typeid: The item type ID
        - last_data: The date of the market snapshot
        
    These three columns form a composite primary key - each item in each
    region has one market data entry per day.
    """
    # Step 1: Pull data (or use provided CSV)
    if csv_file is None:
        csv_file = pull_market_data()
    else:
        print(f"Using existing CSV file: {csv_file}")
    
    # Step 2: Load and validate with pandera
    df = validate_and_load_csv(csv_file)
    
    # Step 3 & 4: Upsert to PostgreSQL (creates table if not exists)
    db_name = "Snowflake" if crunchy_or_snowflake == "snowflake" else "Crunchy Bridge"
    print(f"Target database: {db_name}")
    
    result = upsert_to_postgres(
        df=df,
        table_name=eve_market_data_table,
        schema=postgres_schema,
        primary_keys=EVE_MARKET_PRIMARY_KEYS,
        crunchy_or_snowflake=crunchy_or_snowflake,
    )
    
    print(f"\n✓ ETL Complete!")
    print(f"  Database: {db_name}")
    print(f"  Table: {postgres_schema}.{eve_market_data_table}")
    print(f"  Inserted: {result['inserted']:,}")
    print(f"  Updated: {result['updated']:,}")
    
    return result


if __name__ == "__main__":
    # =========================================================================
    # TESTING THE FLOW
    # =========================================================================
    #
    # Prerequisites:
    #   1. Set up .env file with Crunchy Bridge credentials:
    #      PGHOST="p.xxx.db.postgresbridge.com"
    #      PGDATABASE="postgres"
    #      PGUSER="application"
    #      PGPASSWORD="your-password"
    #
    #   2. Install dependencies:
    #      uv sync
    #
    # Run options:
    #
    #   Option 1: Test with existing CSV (fastest, no API calls)
    #   ---------------------------------------------------------
    #   uv run prefect_test.py
    #
    #   Option 2: Pull fresh data from EVE API
    #   ---------------------------------------------------------
    #   Modify the call below to: load_eve_market_data(csv_file=None)
    #
    #   Option 3: Run as Prefect deployment (requires Prefect Cloud)
    #   ---------------------------------------------------------
    #   prefect deployment run 'load-eve-market-data/eve-market-etl'
    #
    # Verify results in PostgreSQL:
    #   SELECT COUNT(*) FROM eve_online.eve_market_data;
    #   SELECT * FROM eve_online.eve_market_data LIMIT 10;
    #
    # =========================================================================
    
    load_eve_market_data()
