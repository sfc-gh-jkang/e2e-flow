# Snowflake SPCS Deployment Guide

**Reference Implementation:** [cortex-cost-app-spcs](https://github.com/sfc-gh-jkang/cortex-cost-app-spcs)

This guide provides detailed instructions for deploying your application to Snowflake SPCS (Snowpark Container Services).

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Initial Setup](#initial-setup)
- [Deployment Process](#deployment-process)
- [Post-Deployment](#post-deployment)
- [Updating Your Service](#updating-your-service)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## Prerequisites

### Required Software

1. **Docker Desktop**
   - [Download Docker](https://www.docker.com/products/docker-desktop)
   - Ensure Docker is running: `docker ps`

2. **Snowflake CLI**
   ```bash
   # macOS
   brew install snowflake-cli
   
   # or via pip
   pip install snowflake-cli-labs
   
   # Verify
   snow --version
   ```

### Snowflake Requirements

- Active Snowflake account with SPCS enabled
- ACCOUNTADMIN role or custom role with these privileges:
  - CREATE DATABASE
  - CREATE COMPUTE POOL
  - CREATE IMAGE REPOSITORY
  - CREATE SERVICE
  - USAGE on COMPUTE POOL

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Snowflake Account                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ E2E_FLOW_DB (Database)                              │    │
│  │                                                      │    │
│  │  ┌──────────────────┐  ┌──────────────────┐        │    │
│  │  │ IMAGE_SCHEMA     │  │ APP_SCHEMA       │        │    │
│  │  │                  │  │                  │        │    │
│  │  │ - IMAGE_REPO     │  │ - APP_STAGE      │        │    │
│  │  │   (Docker imgs)  │  │ - E2E_FLOW_      │        │    │
│  │  │                  │  │   SERVICE        │        │    │
│  │  └──────────────────┘  └──────────────────┘        │    │
│  │                                                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ E2E_FLOW_COMPUTE_POOL                               │    │
│  │ - Runs containerized services                       │    │
│  │ - Auto-suspend/resume                               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Initial Setup

### 1. Configure Snowflake CLI

```bash
# Interactive setup
snow connection add

# You'll be prompted for:
# - Connection name (e.g., "default")
# - Account identifier
# - Username
# - Password or authentication method
# - Role
# - Warehouse
```

### 2. Test Your Connection

```bash
snow connection test -c default

# Should see: Connection test succeeded
```

### 3. Create Snowflake Infrastructure

Option A: Using Snowflake CLI (recommended)
```bash
snow sql -f snowflake-setup.sql -c default
```

Option B: Using Snowsight
1. Open Snowsight web interface
2. Copy contents of `snowflake-setup.sql`
3. Paste and execute in a worksheet

This creates:
- Database: `E2E_FLOW_DB`
- Schemas: `IMAGE_SCHEMA` (for images), `APP_SCHEMA` (for service)
- Image repository: `IMAGE_REPO`
- Compute pool: `E2E_FLOW_COMPUTE_POOL`
- Stage: `APP_STAGE` (for service specs)

### 4. Verify Setup

```bash
# Check compute pool
snow sql -q "SHOW COMPUTE POOLS;" -c default

# Check image repository
snow sql -q "SHOW IMAGE REPOSITORIES IN SCHEMA E2E_FLOW_DB.IMAGE_SCHEMA;" -c default

# Check stage
snow sql -q "LIST @E2E_FLOW_DB.APP_SCHEMA.APP_STAGE;" -c default
```

---

## Deployment Process

### First Deployment

```bash
./deploy.sh
```

This performs the following steps automatically:

1. **Connection Test** ✅
   - Verifies Snowflake CLI connection

2. **Image Build** 🐳
   - Builds Docker image for linux/amd64
   - Tags for Snowflake registry

3. **Registry Login** 🔐
   - Authenticates with Snowflake's Docker registry
   - Uses `SYSTEM$REGISTRY_LOGIN()`

4. **Image Push** ⬆️
   - Pushes image to Snowflake image repository

5. **Service Spec Upload** 📤
   - Uploads `spcs-service-spec.yaml` to stage

6. **Service Creation** 🚀
   - Creates SPCS service
   - Configures compute pool
   - Sets up endpoints

7. **Health Check** ⏳
   - Waits for service to be READY
   - Maximum wait: 60 seconds

8. **Success** ✨
   - Displays service endpoint URL
   - Shows useful management commands

### Deployment Output Example

```
🔌 Testing Snowflake connection...
✅ Connected to Snowflake
📦 Getting image repository URL...
📍 Target image: orgname-account.registry.snowflakecomputing.com/e2e_flow_db/image_schema/image_repo/e2e-flow:latest

🐳 Building Docker image for linux/amd64...
✅ Build complete!

🏷️  Tagging image...
🔐 Logging into Snowflake registry...
⬆️  Pushing image to Snowflake...
📤 Uploading service specification...

🆕 Creating new service...
   ✅ Service created!

⏳ Waiting for service to be ready...
✅ Service is READY!

🔗 Getting service endpoint...

============================================
✨ Deployment Successful!
============================================
🌐 Service URL: https://xyz-e2e-flow.snowflakecomputing.app

📊 Useful commands:
   Status:  snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default
   Logs:    snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
============================================
```

---

## Post-Deployment

### Verify Service is Running

```bash
# Check service status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# Should return JSON with status: "READY"
```

### Get Service Endpoint

```bash
snow sql -q "SHOW ENDPOINTS IN SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE;" -c default
```

### View Service Logs

```bash
# Last 100 lines
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default

# Last 500 lines
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 500);" -c default
```

### Access Your Application

Open the service URL in your browser (displayed at end of deployment).

---

## Updating Your Service

### Method 1: Using --update Flag (Recommended)

This preserves your ingress URL and is faster:

```bash
./deploy.sh --update
```

What it does:
1. Builds new image
2. Pushes to repository
3. Suspends service
4. Resumes service (automatically pulls new image)
5. Keeps same endpoint URL ✨

### Method 2: Full Redeployment

This creates a new service and generates a new URL:

```bash
./deploy.sh
```

### Local Testing Before Deployment

Always test locally first:

```bash
# Build and run locally
./test-local-container.sh --build

# Test in browser
# http://localhost:8080

# View logs
./test-local-container.sh --logs

# Stop when done
./test-local-container.sh --stop
```

---

## Monitoring & Troubleshooting

### Service Status

```bash
# Detailed status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# All services
snow sql -q "SHOW SERVICES IN SCHEMA E2E_FLOW_DB.APP_SCHEMA;" -c default
```

### Compute Pool Monitoring

```bash
# List all compute pools
snow sql -q "SHOW COMPUTE POOLS;" -c default

# Specific pool details
snow sql -q "DESCRIBE COMPUTE POOL E2E_FLOW_COMPUTE_POOL;" -c default
```

### Image Management

```bash
# List images in repository
snow sql -q "SHOW IMAGES IN IMAGE REPOSITORY E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO;" -c default

# Check image details
snow sql -q "DESCRIBE IMAGE E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO/e2e-flow:latest;" -c default
```

### Common Issues

#### Issue: Service stuck in "PENDING" state

**Solution:**
```bash
# Check compute pool
snow sql -q "SHOW COMPUTE POOLS;" -c default

# Restart service
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;" -c default
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;" -c default
```

#### Issue: "Cannot connect to Snowflake"

**Solution:**
```bash
# Test connection
snow connection test -c default

# Reconfigure if needed
snow connection add
```

#### Issue: Container crashes immediately

**Solution:**
```bash
# Check logs
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 200);" -c default

# Test locally
./test-local-container.sh --build
./test-local-container.sh --logs
```

#### Issue: Out of memory errors

**Solution:** Edit `spcs-service-spec.yaml`:
```yaml
resources:
  requests:
    memory: 2Gi  # Increase this
    cpu: 1.0
  limits:
    memory: 4Gi  # And this
    cpu: 2.0
```

Then redeploy:
```bash
./deploy.sh --update
```

---

## Cost Management

### Suspend Service When Not In Use

```bash
# Suspend (stops billing)
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;" -c default

# Resume when needed
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;" -c default
```

### Auto-Suspend Compute Pool

The compute pool is configured to auto-suspend after 1 hour of inactivity (see `snowflake-setup.sql`).

---

## Advanced Topics

### Using Different Environments

```bash
# Development
./deploy.sh --connection dev

# Production
./deploy.sh --connection prod
```

### Custom Image Tags

Edit `deploy.sh`:
```bash
IMAGE_TAG="v1.0.0"  # Instead of "latest"
```

### Multiple Services

Duplicate and modify:
1. `spcs-service-spec.yaml` → `spcs-service-spec-v2.yaml`
2. Update `SERVICE_NAME` in `deploy.sh`
3. Deploy

---

## Quick Reference

### Deployment Commands
```bash
./deploy.sh              # First deployment
./deploy.sh --update     # Update existing
./deploy.sh --local      # Build locally only
```

### Status & Logs
```bash
# Status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# Logs
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

### Service Control
```bash
# Suspend
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;" -c default

# Resume
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;" -c default
```

---

## Additional Resources

- [Snowflake SPCS Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)
- [Snowflake CLI Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index)
- [Reference Implementation](https://github.com/sfc-gh-jkang/cortex-cost-app-spcs)
- [QUICKSTART.md](QUICKSTART.md) - Quick reference guide
- [README.md](README.md) - Complete documentation

---

**Need help?** Check the troubleshooting section or review service logs.



