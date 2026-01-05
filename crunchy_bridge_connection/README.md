# Crunchy Bridge Connection

PostgreSQL connection utilities for Crunchy Bridge.

## Setup

1. Add Crunchy Bridge credentials to your `.env` file using standard PostgreSQL variables:

```bash
PGHOST="p.EXAMPLE.db.postgresbridge.com"
PGDATABASE="postgres"
PGUSER="application"
PGPASSWORD="your-password"
PGPORT=5432  # optional, defaults to 5432
```

1. Install dependencies (already added to pyproject.toml):

```bash
uv sync
```

## Usage

### Test Connection

```bash
python -m crunchy_bridge_connection.connection
```

### Load CSV to Table

```python
from dotenv import load_dotenv
from crunchy_bridge_connection import load_csv_to_table

load_dotenv()

# Load CSV, auto-creating the table
rows = load_csv_to_table(
    "eve_online_data/eve_market_all_a4e_regions_20251203_135659.csv",
    "eve_market_data",
    drop_existing=True  # Replace existing table
)
print(f"Loaded {rows} rows")
```

### Command Line

```bash
# Load CSV file
python -m crunchy_bridge_connection.csv_loader path/to/file.csv table_name

# Load and replace existing table
python -m crunchy_bridge_connection.csv_loader path/to/file.csv table_name --drop
```

### Direct Connection

```python
from dotenv import load_dotenv
from crunchy_bridge_connection import get_connection

load_dotenv()

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM eve_market_data LIMIT 10")
        for row in cur.fetchall():
            print(row)
```

## Features

- **Standard PG variables**: Uses `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
- **Auto type inference**: Detects INTEGER, FLOAT, BOOLEAN, or TEXT from CSV data
- **Efficient bulk loading**: Uses PostgreSQL COPY for fast imports
- **SSL by default**: Secure connections to Crunchy Bridge
- **Column name sanitization**: Handles spaces and special characters

## OpenFlow CDC Replication Setup

To enable OpenFlow to read changes from PostgreSQL (Crunchy or Snowflake) into Snowflake
normal tables via Change Data Capture (CDC), you must configure replication on the source database.

### Setup Steps (Run on BOTH Crunchy and Snowflake PostgreSQL)

```sql
-- 1. Create a replication user with password
CREATE USER replication_user WITH REPLICATION PASSWORD 'your-secure-password';

-- 2. Ensure the user has replication privileges
ALTER USER replication_user WITH REPLICATION;

-- 3. Set REPLICA IDENTITY FULL on tables you want to replicate
--    This allows OpenFlow to capture UPDATE and DELETE changes (not just INSERTs)
ALTER TABLE eve_online.eve_market_data REPLICA IDENTITY FULL;
```

### Why REPLICA IDENTITY FULL?

- **DEFAULT**: Only logs primary key columns for UPDATE/DELETE - may miss changes if no PK
- **FULL**: Logs all column values - required for proper CDC when you need complete row data
- OpenFlow needs FULL to correctly replicate all changes to Snowflake tables

### Apply to Additional Tables

For each table you want to replicate:

```sql
ALTER TABLE schema_name.table_name REPLICA IDENTITY FULL;
```

### Create a Publication

OpenFlow Connector for PostgreSQL requires a publication to be created and configured
before replication starts. You can create it for all tables, a subset of tables, or
specific tables with specified columns only.

**Step 1: Create the publication**

For PostgreSQL 13 and later:

```sql
CREATE PUBLICATION eve_market_publication WITH (publish_via_partition_root = true);
```

> The `publish_via_partition_root` option is needed for correct replication of partitioned tables.

For PostgreSQL versions earlier than 13:

```sql
CREATE PUBLICATION eve_market_publication;
```

**Step 2: Add tables to the publication**

```sql
-- Add specific tables
ALTER PUBLICATION eve_market_publication ADD TABLE eve_online.eve_market_data;

-- Or add multiple tables
ALTER PUBLICATION eve_market_publication ADD TABLE schema.table1, schema.table2;
```

For partitioned tables, just add the root partition table to the publication.

**Verify the publication:**

```sql
-- List all publications
SELECT * FROM pg_publication;

-- List tables in a publication
SELECT * FROM pg_publication_tables WHERE pubname = 'eve_market_publication';
```
