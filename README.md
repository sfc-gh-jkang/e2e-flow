# E2E Flow - Prefect Worker on Snowflake SPCS

End-to-end flow setup with **Prefect worker running on Snowflake SPCS** (Snowpark Container Services) using UV and Ubuntu.

**Based on:** [cortex-cost-app-spcs](https://github.com/sfc-gh-jkang/cortex-cost-app-spcs)

**Reference:** Prefect docs for ECS worker setup: <https://docs.prefect.io/integrations/prefect-aws/ecs-worker/manual-deployment>

## 🎯 What This Does

- Pulls data from: ...


This project runs a **Prefect worker pool inside Snowflake SPCS** that:

- ✅ Connects to Prefect Cloud over HTTPS (port 443)
- ✅ Executes flow runs from your Prefect workspace
- ✅ Runs within your Snowflake account's security boundary
- ✅ Uses UV for ultra-fast Python package management

## ✅ Step 1: Setup a Snowflake SPCS UV Ubuntu container with Docker

This project includes a complete setup for running a Prefect worker on Snowflake SPCS with UV (ultra-fast Python package installer).

### 📁 Project Structure

```text
e2e-flow/
├── Dockerfile                 # Ubuntu-based container with UV
├── docker-compose.yml         # Local development setup
├── .dockerignore             # Docker build exclusions
├── spcs-service-spec.yaml    # Snowflake SPCS service specification
├── snowflake-setup.sql       # SQL commands for Snowflake infrastructure
├── deploy.sh                 # Main SPCS deployment script (uses Snowflake CLI)
├── build-and-push-spcs.sh    # Alternative SPCS deployment script
├── build-and-push-github.sh  # GitHub Container Registry build & push script
├── test-local-container.sh   # Local container testing script
├── setup-prefect-env.sh      # Prefect environment setup script
├── get-prefect-url.sh        # Get Prefect API URL helper
├── pyproject.toml            # Python project configuration (with Prefect)
├── main.py                   # Prefect worker entry point
└── docs/                     # Documentation
    ├── QUICKSTART.md         # Quick start guide
    ├── DEPLOYMENT_GUIDE.md   # Detailed deployment guide
    ├── PREFECT_SETUP.md      # Prefect configuration
    ├── CREATE_WORK_POOL.md   # Work pool creation guide
    ├── PREFECT_AUTH.md       # Authentication methods
    ├── GET_PREFECT_URL.md    # Getting API URL guide
    └── CHANGES.md            # Changelog
```

### 🚀 Quick Start - Local Testing

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

Before configuring the service, create a work pool:

1. Log into [Prefect Cloud](https://app.prefect.cloud)
2. Go to **Work Pools** → **Create Work Pool**
3. Name: `spcs-process`, Type: **Process**

Or via CLI:

```bash
uv run prefect cloud login -k pnu_your_key
uv run prefect work-pool create spcs-process --type process
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
- [ ] Create Prefect flows and deployments
- [ ] Add health check endpoint
- [ ] Implement monitoring and alerting
- [ ] Set up CI/CD pipeline
- [ ] Add environment-specific configurations
- [ ] Implement proper logging and error handling

---

**🎉 You now have a Prefect worker running on Snowflake SPCS!** The worker connects to Prefect Cloud and can execute your flow runs within your Snowflake account.
