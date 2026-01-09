# E2E Flow - Prefect Worker on Prefect Cloud

**Based on:** [cortex-cost-app-spcs](https://github.com/sfc-gh-jkang/cortex-cost-app-spcs)

**Reference:** Prefect docs for ECS worker setup: <https://docs.prefect.io/integrations/prefect-aws/ecs-worker/manual-deployment>

## 🎯 What This Does

**EVE Online Market Data ETL Pipeline** that:

- 📊 Pulls daily market data from EVE Online ESI API
- ✅ Validates data with Pandera schemas
- 💾 Loads to **Crunchy Bridge PostgreSQL** OR **Snowflake PostgreSQL**
- 🔄 Supports upsert (merge) operations with primary keys
- 🐳 Runs in Docker containers on Google Cloud VM

This project runs **Prefect workers on a Google VM** with two work pools:

- **`google-vm`** - Process-based worker for direct execution
- **`google-vm-docker`** - Docker-based worker for containerized flows

Features:

- ✅ Connects to Prefect Cloud over HTTPS (port 443)
- ✅ Executes flow runs from your Prefect workspace
- ✅ Dual database support: Crunchy Bridge + Snowflake PostgreSQL
- ✅ Uses UV for ultra-fast Python package management

## ✅ Infrastructure Setup

This project supports multiple deployment methods:

1. **Google VM with Docker** (current active setup) - See `google_compute_quickstart.md`
2. **Snowflake SPCS** - Container services within Snowflake

Both use UV (ultra-fast Python package installer) and Docker containers.

### 📁 Project Structure

```text
e2e-flow/
├── Dockerfile                 # Ubuntu-based container with UV
├── docker-compose.yml         # Local development setup
├── prefect.yaml              # Prefect deployments configuration
├── prefect_test.py           # EVE Online ETL flow and tasks
├── docker_cleanup.py         # Docker cleanup maintenance flow
├── main.py                   # Prefect worker entry point
├── pyproject.toml            # Python project configuration
├── google_compute_quickstart.md  # Google VM setup guide
│
├── crunchy_bridge_connection/    # PostgreSQL utilities
│   ├── connection.py         # Database connection (Crunchy + Snowflake)
│   ├── csv_loader.py         # CSV loading, upsert, and CLI tools
│   └── README.md             # Module documentation
│
├── eve_online_data/          # EVE Online market data module
│   ├── __init__.py           # Data fetching and validation
│   └── *.csv                 # Downloaded market data files
│
├── docs/                     # Documentation
│   ├── QUICKSTART.md         # Quick start guide
│   ├── DEPLOYMENT_GUIDE.md   # Detailed deployment guide
│   └── ...                   # Additional guides
│
└── scripts/                  # Deployment scripts
    ├── deploy.sh             # SPCS deployment script
    ├── build-and-push-github.sh  # GitHub Container Registry script
    └── test-local-container.sh   # Local testing script
```

## 📊 EVE Online ETL Pipeline

### Prefect Deployments

The project includes 4 Prefect deployments configured in `prefect.yaml`:

| Deployment | Target DB | Work Pool | Schedule |
|------------|-----------|-----------|----------|
| `eve-market-etl` | Crunchy | `google-vm` | 6 AM UTC |
| `docker-eve-market-etl` | Crunchy | `google-vm-docker` | 7 AM UTC |
| `docker-sf-eve-market-etl` | Snowflake | `google-vm-docker` | 8 AM UTC |
| `docker-cleanup` | N/A | `google-vm` | 8 AM UTC |

### Running the ETL Locally

```bash
# Run ETL to Crunchy Bridge (default)
uv run python -c "from prefect_test import load_eve_market_data; load_eve_market_data()"

# Run ETL to Snowflake PostgreSQL
uv run python -c "from prefect_test import load_eve_market_data; load_eve_market_data(crunchy_or_snowflake='snowflake')"
```

### Querying EVE Market Data from Snowflake

The EVE Online market data is available in multiple Snowflake databases. Connect to your Snowflake account to query the data.

#### Available Databases

| Database | Purpose | Description |
|----------|---------|-------------|
| `EVE_ONLINE` | Raw market data | Main source from ESI API via OpenFlow CDC |
| `EVE_ONLINE_CRUNCHY` | Crunchy Bridge mirror | Data replicated from Crunchy Bridge PostgreSQL |
| `EVE_ONLINE_DBT_DB_DEV` | dbt transformations (dev) | Staging and mart views with cleaned data |
| `EVE_ONLINE_DBT_DB_PROD` | dbt transformations (prod) | Production-ready transformed data |

#### Raw Data Queries

```sql
-- Check latest data in raw table
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT REGION_ID) as unique_regions,
    COUNT(DISTINCT TYPEID) as unique_items,
    MAX(TIMESTAMP_PULLED) as latest_pull
FROM EVE_ONLINE.EVE_ONLINE.EVE_MARKET_DATA
WHERE _SNOWFLAKE_DELETED = FALSE;

-- Get sample of most recent records
SELECT *
FROM EVE_ONLINE.EVE_ONLINE.EVE_MARKET_DATA
ORDER BY TIMESTAMP_PULLED DESC
LIMIT 10;

-- Daily pull summary
SELECT 
    DATE(TIMESTAMP_PULLED) as pull_date,
    COUNT(*) as records_pulled,
    COUNT(DISTINCT REGION_NAME) as regions,
    COUNT(DISTINCT ITEM_NAME) as items
FROM EVE_ONLINE.EVE_ONLINE.EVE_MARKET_DATA
WHERE _SNOWFLAKE_DELETED = FALSE
GROUP BY DATE(TIMESTAMP_PULLED)
ORDER BY pull_date DESC
LIMIT 10;

-- Top regions by record count
SELECT 
    REGION_NAME,
    COUNT(*) as record_count,
    MAX(TIMESTAMP_PULLED) as last_update
FROM EVE_ONLINE.EVE_ONLINE.EVE_MARKET_DATA
WHERE _SNOWFLAKE_DELETED = FALSE
GROUP BY REGION_NAME
ORDER BY record_count DESC;
```

#### Transformed Data Queries (dbt)

The dbt models provide cleaned and enriched data with resolved item names.

```sql
-- Query the mart view with cleaned item names
SELECT *
FROM EVE_ONLINE_DBT_DB_DEV.MARTS.EVE_MARKET_WITH_ITEM_NAMES
ORDER BY LAST_DATA DESC
LIMIT 10;

-- Get summary of transformed data
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT ITEM_NAME) as unique_items,
    MAX(TIMESTAMP_PULLED) as latest_pull,
    MAX(LAST_DATA) as latest_data_date
FROM EVE_ONLINE_DBT_DB_DEV.MARTS.EVE_MARKET_WITH_ITEM_NAMES;

-- Lookup item name mappings
SELECT *
FROM EVE_ONLINE_DBT_DB_DEV.MARTS.ITEM_NAME_MAP
ORDER BY TYPEID
LIMIT 20;

-- Query staging layer (raw with casted timestamps)
SELECT *
FROM EVE_ONLINE_DBT_DB_DEV.STAGING.RAW_EVE_MARKET
WHERE REGION_NAME = 'The Forge'
ORDER BY LAST_DATA DESC
LIMIT 10;
```

#### dbt Model Structure

```
EVE_ONLINE_DBT_DB_DEV/
├── STAGING/
│   └── RAW_EVE_MARKET (view)         # Raw data with casted timestamps/dates
└── MARTS/
    ├── ITEM_NAME_MAP (view)          # TypeID → Item Name mapping
    └── EVE_MARKET_WITH_ITEM_NAMES (view)  # Cleaned market data with resolved names
```

**Key Transformations:**
- Timestamps are properly cast from strings
- "Unknown" item names are resolved via the `ITEM_NAME_MAP`
- Deleted rows (`_SNOWFLAKE_DELETED = TRUE`) are filtered out
- Data is ordered by `LAST_DATA DESC, REGION_ID ASC, TYPEID ASC`

### Testing Database Connections

```bash
# Test Crunchy Bridge connection
uv run python -c "from crunchy_bridge_connection.connection import test_connection; test_connection()"

# Test Snowflake PostgreSQL connection
uv run python -c "from crunchy_bridge_connection.connection import test_connection; test_connection(crunchy_or_snowflake='snowflake')"
```

### CSV Loader CLI

```bash
# Load CSV to table (uses COPY - fast bulk load)
uv run python -m crunchy_bridge_connection.csv_loader load <csv_file> <table_name> --schema eve_online

# Upsert CSV to table (uses INSERT ON CONFLICT - merges data)
uv run python -m crunchy_bridge_connection.csv_loader upsert <csv_file> <table_name> \
  --primary-keys region_id,typeid,last_data --schema eve_online

# Pull table to CSV
uv run python -m crunchy_bridge_connection.csv_loader pull eve_online.eve_market_data

# Add --snowflake flag to target Snowflake instead of Crunchy
uv run python -m crunchy_bridge_connection.csv_loader pull eve_online.eve_market_data --snowflake
```

### Environment Variables

Create a `.env` file with:

```bash
# Crunchy Bridge PostgreSQL
PGHOST="p.EXAMPLE.db.postgresbridge.com"
PGDATABASE="postgres"
PGUSER="application"
PGPASSWORD="your-password"

# Snowflake PostgreSQL (wire protocol)
SNOWFLAKE_POSTGRES_HOST="your-account.snowflakecomputing.com"
SNOWFLAKE_POSTGRES_USER="your-user"
SNOWFLAKE_POSTGRES_PASSWORD="your-password"
SNOWFLAKE_POSTGRES_DATABASE="your-database"

# Prefect Cloud
PREFECT_API_URL="https://api.prefect.cloud/api/accounts/.../workspaces/..."
PREFECT_API_KEY="pnu_..."
```

---

## 🚀 Quick Start - Local Testing

**Option 1: Using the test script (recommended)**

```bash
# Build and run
./test-local-container.sh --build

# View logs
./test-local-container.sh --logs

# Open shell
./test-local-container.sh --shell

# Stop container
./test-local-container.sh --stop
```

**Option 2: Using Docker Compose**

```bash
docker-compose up --build
```

**Option 3: Using Docker directly**

```bash
docker build --platform linux/amd64 -t e2e-flow:latest .
docker run -p 8080:8080 e2e-flow:latest
```

### 🐙 GitHub Container Registry

Push your Docker image to GitHub Container Registry for easy sharing and deployment:

**Setup (one-time):**

```bash
# 1. Create a GitHub Personal Access Token
#    Go to: https://github.com/settings/tokens
#    Scopes: write:packages, read:packages

# 2. Export the token
export CR_PAT=your_token_here

# 3. Login to GitHub Container Registry
echo $CR_PAT | docker login ghcr.io -u your-github-username --password-stdin
```

**Build and push:**

```bash
# Build and push to GitHub Container Registry
./build-and-push-github.sh

# Build only (don't push)
./build-and-push-github.sh --local

# Build with custom tag
./build-and-push-github.sh --tag v1.0.0

# Build without cache
./build-and-push-github.sh --no-cache

# Show help
./build-and-push-github.sh --help
```

Your image will be available at: `ghcr.io/your-username/e2e-flow:latest`

### ☁️ Snowflake SPCS Deployment

#### Prerequisites

- **Docker** installed and running
- **Snowflake CLI** installed ([Installation Guide](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation))
- **Snowflake account** with SPCS enabled
- **Appropriate privileges** (ACCOUNTADMIN or custom role with SPCS permissions)

#### Step 1: Install Snowflake CLI

```bash
# macOS (using Homebrew)
brew install snowflake-cli

# Or using pip
pip install snowflake-cli-labs

# Verify installation
snow --version
```

#### Step 2: Configure Snowflake Connection

```bash
# Add a new connection
snow connection add

# Or test existing connection
snow connection test -c default

# List available connections
snow connection list
```

#### Step 3: Set up Snowflake Infrastructure

Run the setup SQL in Snowflake (via Snowsight or SnowSQL):

```bash
# Option 1: Using Snowflake CLI
snow sql -f snowflake-setup.sql -c default

# Option 2: Copy and paste into Snowsight
# Open snowflake-setup.sql and execute the commands
```

This creates:

- Database: `E2E_FLOW_DB`
- Schemas: `IMAGE_SCHEMA`, `APP_SCHEMA`
- Image repository: `IMAGE_REPO`
- Compute pool: `E2E_FLOW_COMPUTE_POOL`
- Application stage: `APP_STAGE`

#### Step 4: Deploy to Snowflake

**First deployment (creates new service + ingress URL):**

```bash
./deploy.sh
```

**Update existing service (preserves ingress URL):**

```bash
./deploy.sh --update
```

**Local development mode:**

```bash
./deploy.sh --local
```

**Using a specific connection:**

```bash
./deploy.sh --connection my-connection
```

The deploy script will:

1. ✅ Test Snowflake connection
2. 🐳 Build Docker image for linux/amd64
3. 🏷️ Tag image for Snowflake registry
4. 🔐 Authenticate with Snowflake registry
5. ⬆️ Push image to repository
6. 📤 Upload service specification
7. 🚀 Create or update the service
8. ⏳ Wait for service to be ready
9. 🔗 Display service endpoint URL

#### Step 5: Create Work Pool in Prefect Cloud

Before configuring the service, create a work pool. Choose based on your deployment method:

**For Snowflake SPCS deployment:**

- Name: `spcs-process`, Type: **Process**

**For Google VM deployment (current active setup):**

- Name: `google-vm`, Type: **Process** (direct execution)
- Name: `google-vm-docker`, Type: **Docker** (containerized flows)

Via CLI:

```bash
uv run prefect cloud login -k pnu_your_key

# For SPCS
uv run prefect work-pool create spcs-process --type process

# For Google VM
uv run prefect work-pool create google-vm --type process
uv run prefect work-pool create google-vm-docker --type docker
```

📖 **Detailed guide:** See [CREATE_WORK_POOL.md](docs/CREATE_WORK_POOL.md)

#### Step 6: Configure Prefect Environment Variables

After deployment, set your Prefect Cloud credentials:

```sql
-- Set Prefect API URL
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_URL = 'https://api.prefect.cloud/api/accounts/<your-account-id>/workspaces/<your-workspace-id>';

-- Set Prefect API Key
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_KEY = 'pnu_your_api_key_here';

-- Set Work Pool (optional, defaults to "spcs-process")
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_WORK_POOL = 'spcs-process';

-- Restart service to apply changes
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;
```

**Get your Prefect credentials:**

- Log into [Prefect Cloud](https://app.prefect.cloud)
- API URL: Settings → General → Copy API URL
- API Key: Settings → API Keys → Create API Key

📖 **Detailed Prefect setup:** See [PREFECT_SETUP.md](docs/PREFECT_SETUP.md)

#### Step 7: Verify Agent Connection

Check the logs to confirm your Prefect agent is connected:

```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

You should see:

```text
🚀 Starting Prefect worker on Snowflake SPCS...
✅ Connected to Prefect Cloud: https://api.prefect.cloud/api/accounts/...
✅ Work Pool: spcs-process
✅ Starting Prefect worker...
   Running: prefect worker start --pool spcs-process

Starting worker connected to https://api.prefect.cloud/api/accounts/...
Worker started! Looking for work from work pool 'spcs-process'...
```

Then check Prefect Cloud → **Work Pools** → **spcs-process** to see your worker online! 🎉

## 📋 Commands Reference

### 🐙 GitHub Container Registry Commands

```bash
# Build and push to GitHub Container Registry
./build-and-push-github.sh

# Build only (don't push)
./build-and-push-github.sh --local

# Build with custom tag
./build-and-push-github.sh --tag v1.0.0

# Build without cache
./build-and-push-github.sh --no-cache

# Show help
./build-and-push-github.sh --help
```

### 🚀 Snowflake SPCS Deployment Commands

```bash
# First deployment (creates new service + ingress URL)
./deploy.sh

# Update existing service (preserves ingress URL)
./deploy.sh --update

# Local development mode (build only)
./deploy.sh --local

# Use specific Snowflake connection
./deploy.sh --connection my-connection

# Show help
./deploy.sh --help
```

### 🐳 Local Testing Commands

```bash
# Build and run container
./test-local-container.sh --build

# Run with existing image
./test-local-container.sh

# View logs
./test-local-container.sh --logs

# Open shell in container
./test-local-container.sh --shell

# Stop container
./test-local-container.sh --stop

# Run tests
./test-local-container.sh --test
```

### 🔍 Service Management (using Snowflake CLI)

```bash
# Check service status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# View service logs (last 100 lines)
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default

# Show service endpoints
snow sql -q "SHOW ENDPOINTS IN SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE;" -c default

# Show all services
snow sql -q "SHOW SERVICES IN SCHEMA E2E_FLOW_DB.APP_SCHEMA;" -c default

# Show images in repository
snow sql -q "SHOW IMAGES IN IMAGE REPOSITORY E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO;" -c default

# Suspend service (stops billing)
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;" -c default

# Resume service
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;" -c default

# Show compute pools
snow sql -q "SHOW COMPUTE POOLS;" -c default
```

### 🔧 Container Features

- **Base Image:** Python 3.13 Slim
- **Python Version:** 3.13
- **Package Manager:** UV (ultra-fast Python package installer)
- **Architecture:** linux/amd64 (required for Snowflake SPCS)
- **Port:** 8080 (configurable)
- **Prefect:** Worker connects to Prefect Cloud
- **Network:** Outbound HTTPS (port 443) enabled for Prefect Cloud

### 📦 UV Benefits

- **Speed:** 10-100x faster than pip
- **Reliability:** Better dependency resolution
- **Compatibility:** Drop-in replacement for pip
- **Efficiency:** Parallel downloads and installations

### 🏗️ Multi-Stage Build Benefits

The Dockerfile uses a multi-stage build approach with two stages:

**Builder Stage:**

- Installs build tools (gcc, g++, git)
- Creates virtual environment with all dependencies
- Compiles native extensions if needed

**Runtime Stage:**

- Only copies the compiled virtual environment
- Minimal runtime dependencies (libgomp1, ca-certificates)
- No build tools = smaller image size

**Advantages:**

- **Smaller images:** 40-60% reduction in final image size
- **Faster deployments:** Less data to push/pull
- **Better security:** Reduced attack surface (no compiler tools)
- **Lower costs:** Reduced storage and transfer costs

### 🛠️ Customization

#### Adding Python Dependencies

Edit `pyproject.toml`:

```toml
[project]
dependencies = [
    "prefect>=2.14.0",
    "prefect-snowflake>=0.27.0",
    # Add your additional dependencies here
    "pandas>=2.0.0",
    "requests>=2.31.0",
]
```

#### Configuring Prefect Worker

The worker is configured via environment variables. Set them in Snowflake:

```sql
-- Required
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_URL = 'your-prefect-api-url';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_KEY = 'your-prefect-api-key';

-- Optional: Specify work pool
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_WORKER_POOL_NAME = 'my-spcs-pool';
```

#### Modifying Resources

Edit `spcs-service-spec.yaml`:

```yaml
resources:
  requests:
    memory: 2Gi  # Adjust as needed
    cpu: 1.0     # Adjust as needed
```

#### Changing Python Version

Edit the base image in both stages of the `Dockerfile`:

```dockerfile
# Stage 1: Build stage
FROM python:3.13-slim AS builder  # Change to desired version

# Stage 2: Runtime stage
FROM python:3.13-slim  # Change to match builder version
```

### 📚 Additional Resources

- [Snowflake SPCS Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)
- [UV Documentation](https://github.com/astral-sh/uv)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### 🐛 Troubleshooting

**Snowflake CLI not found:**

```bash
# Install Snowflake CLI
brew install snowflake-cli  # macOS
# or
pip install snowflake-cli-labs
```

**Connection issues:**

```bash
# List available connections
snow connection list

# Test connection
snow connection test -c default

# Add new connection
snow connection add
```

**Build fails:**

- Ensure Docker is running
- Check Docker has enough resources (memory/CPU)
- Verify platform is set to linux/amd64

**Deployment fails:**

- Check Snowflake connection: `snow connection test -c default`
- Verify compute pool is active: `SHOW COMPUTE POOLS;`
- Check image repository exists: `SHOW IMAGE REPOSITORIES;`
- Ensure proper privileges (need SPCS permissions)

**Service fails to start:**

```bash
# Check compute pool status
snow sql -q "DESCRIBE COMPUTE POOL E2E_FLOW_COMPUTE_POOL;" -c default

# Check service status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# View service logs
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default

# Verify image exists
snow sql -q "SHOW IMAGES IN IMAGE REPOSITORY E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO;" -c default
```

**Service endpoint not working:**

- Wait 1-2 minutes for service to be fully ready
- Check service status shows "READY"
- Verify endpoint is public in spcs-service-spec.yaml
- Check container logs for errors

**Container crashes:**

- Review logs: `./deploy.sh` output or `snow sql` logs command
- Test locally first: `./test-local-container.sh --build`
- Check resource limits in spcs-service-spec.yaml
- Verify all dependencies are in pyproject.toml

### 💡 Best Practices

1. **Always use `--update` for subsequent deployments** to preserve your ingress URL
2. **Test locally first** with `./test-local-container.sh --build` before deploying
3. **Monitor your service** regularly using status and logs commands
4. **Suspend services** when not in use to save costs
5. **Use appropriate resource limits** in spcs-service-spec.yaml
6. **Version your images** by changing IMAGE_TAG in deploy.sh

### 🔄 Development Workflow

1. **Make code changes** to your application
2. **Test locally:**

   ```bash
   ./test-local-container.sh --build
   ```

3. **Deploy updates:**

   ```bash
   ./deploy.sh --update
   ```

4. **Monitor deployment:**

   ```bash
   snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default
   ```

5. **Check logs if needed:**

   ```bash
   snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
   ```

### 📚 Documentation

#### Quick References

- **[QUICKSTART.md](docs/QUICKSTART.md)** - 10-minute quick start guide
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Comprehensive deployment guide
- **[PREFECT_SETUP.md](docs/PREFECT_SETUP.md)** - Detailed Prefect worker configuration

#### Prefect Configuration

- **[CREATE_WORK_POOL.md](docs/CREATE_WORK_POOL.md)** - Creating work pools in Prefect Cloud
- **[PREFECT_AUTH.md](docs/PREFECT_AUTH.md)** - Authentication methods explained
- **[GET_PREFECT_URL.md](docs/GET_PREFECT_URL.md)** - Getting your Prefect API URL

#### Technical Details

- **[DOCKERFILE_CHANGES.md](docs/DOCKERFILE_CHANGES.md)** - Dockerfile updates and optimization
- **[PREFECT_CHANGES.md](docs/PREFECT_CHANGES.md)** - Prefect integration changes
- **[CHANGES.md](docs/CHANGES.md)** - Complete changelog

#### External Resources

- [Prefect Documentation](https://docs.prefect.io)
- [Prefect Cloud](https://app.prefect.cloud)
- [Snowflake SPCS Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)
- [Snowflake CLI Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index)
- [UV Documentation](https://github.com/astral-sh/uv)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Reference Implementation](https://github.com/sfc-gh-jkang/cortex-cost-app-spcs)

### 📝 Next Steps

- [x] Configure Prefect integration ✅
- [x] Enable outbound HTTPS for Prefect Cloud ✅
- [x] Create Prefect flows and deployments ✅ (4 deployments in prefect.yaml)
- [x] EVE Online market data ETL pipeline ✅
- [x] Dual database support (Crunchy + Snowflake) ✅
- [x] CSV loader with upsert support ✅
- [x] Docker-based deployments ✅
- [ ] Add health check endpoint
- [ ] Implement monitoring and alerting
- [ ] Set up CI/CD pipeline
- [ ] Add OpenFlow CDC replication to Snowflake tables

---

**🎉 You now have a Prefect worker running!** The worker connects to Prefect Cloud and executes your flow runs.

**Current active setup:** Google VM with Docker-based ETL flows loading EVE Online market data to Crunchy Bridge and Snowflake PostgreSQL databases.
