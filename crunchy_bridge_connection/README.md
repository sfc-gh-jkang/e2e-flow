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

2. Install dependencies (already added to pyproject.toml):

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
