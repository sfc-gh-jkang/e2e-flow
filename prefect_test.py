"""Prefect flows for EVE Online market data ETL pipeline."""

import subprocess
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
def upsert_to_postgres(df, table_name: str, schema: str, primary_keys: list[str]):
    """Upsert DataFrame to PostgreSQL (merge on primary keys)."""
    result = upsert_dataframe_to_table(
        df=df,
        table_name=table_name,
        primary_keys=primary_keys,
        schema=schema,
        create_table=True,  # Creates table with PK if not exists
    )
    return result


@task
def cleanup_docker(keep_images: int = 3, keep_containers: int = 10):
    """
    Clean up old Docker images and containers to prevent disk bloat.
    
    Args:
        keep_images: Number of recent images to keep (default: 3)
        keep_containers: Number of recent containers to keep (default: 10)
        
    Note:
        This task requires Docker socket access. For Docker work pools,
        mount the socket in job_variables:
            job_variables:
              volumes: ["/var/run/docker.sock:/var/run/docker.sock"]
    """
    def run_cmd(cmd: list[str]) -> str:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.stdout.strip()
        except Exception as e:
            print(f"⚠️ Command failed: {' '.join(cmd)} - {e}")
            return ""
    
    # Check if Docker is available
    if not run_cmd(["docker", "--version"]):
        print("⚠️ Docker not available - skipping cleanup")
        return {"images_removed": 0, "containers_removed": 0}
    
    images_removed = 0
    containers_removed = 0
    
    # Clean up old containers (keep last N)
    print(f"🧹 Cleaning up containers (keeping last {keep_containers})...")
    containers = run_cmd(["docker", "ps", "-aq"]).split("\n")
    containers = [c for c in containers if c]  # Remove empty strings
    
    if len(containers) > keep_containers:
        old_containers = containers[keep_containers:]
        for container_id in old_containers:
            run_cmd(["docker", "rm", "-f", container_id])
            containers_removed += 1
        print(f"  Removed {containers_removed} old containers")
    else:
        print(f"  Only {len(containers)} containers - no cleanup needed")
    
    # Clean up old images (keep last N)
    print(f"🧹 Cleaning up images (keeping last {keep_images})...")
    images = run_cmd(["docker", "images", "-q"]).split("\n")
    images = [i for i in images if i]  # Remove empty strings
    
    if len(images) > keep_images:
        old_images = images[keep_images:]
        for image_id in old_images:
            result = run_cmd(["docker", "rmi", "-f", image_id])
            if "Deleted" in result or not result:
                images_removed += 1
        print(f"  Removed {images_removed} old images")
    else:
        print(f"  Only {len(images)} images - no cleanup needed")
    
    # Also prune dangling images and build cache
    print("🧹 Pruning dangling images and build cache...")
    run_cmd(["docker", "image", "prune", "-f"])
    run_cmd(["docker", "builder", "prune", "-f", "--filter", "until=24h"])
    
    print(f"✓ Cleanup complete: {images_removed} images, {containers_removed} containers removed")
    return {"images_removed": images_removed, "containers_removed": containers_removed}


@flow(log_prints=True)
def load_eve_market_data(csv_file: str | None = None):
    """
    ETL flow for EVE Online market data.
    
    1. Pull market data from API (or use provided CSV)
    2. Load and validate CSV with pandera
    3. Create PostgreSQL table if not exists (with primary key)
    4. Upsert (merge) data into Crunchy Bridge PostgreSQL
    
    Args:
        csv_file: Optional path to existing CSV file. If None, pulls fresh data.
        
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
    result = upsert_to_postgres(
        df=df,
        table_name=eve_market_data_table,
        schema=postgres_schema,
        primary_keys=EVE_MARKET_PRIMARY_KEYS,
    )
    
    print(f"\n✓ ETL Complete!")
    print(f"  Table: {postgres_schema}.{eve_market_data_table}")
    print(f"  Inserted: {result['inserted']:,}")
    print(f"  Updated: {result['updated']:,}")
    
    # Step 5: Clean up old Docker images/containers (optional)
    cleanup_docker(keep_images=3, keep_containers=10)
    
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

