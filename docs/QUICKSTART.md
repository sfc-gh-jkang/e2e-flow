# Prefect Worker on Snowflake SPCS - Quick Start Guide

**Based on:** [cortex-cost-app-spcs](https://github.com/sfc-gh-jkang/cortex-cost-app-spcs)

## 🚀 Quick Deployment (10 minutes)

### Step 1: Install Prerequisites

```bash
# Install Snowflake CLI
brew install snowflake-cli

# Verify
snow --version
```

### Step 2: Configure Snowflake

```bash
# Setup connection
snow connection add

# Test it
snow connection test -c default
```

### Step 3: Setup Infrastructure

```bash
# Run setup SQL
snow sql -f snowflake-setup.sql -c default
```

### Step 4: Deploy

```bash
# First time
./deploy.sh
```

### Step 5: Create Work Pool in Prefect Cloud

```bash
# Login to Prefect
uv run prefect cloud login -k pnu_your_api_key_here

# Create work pool
uv run prefect work-pool create spcs-process --type process
```

Or via UI: [Prefect Cloud](https://app.prefect.cloud) → **Work Pools** → **Create Work Pool**

### Step 6: Configure Prefect (Required)

```bash
# Get your Prefect credentials from https://app.prefect.cloud
# Settings → General → Copy API URL
# Settings → API Keys → Create API Key

snow sql -c default << EOF
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_URL = 'https://api.prefect.cloud/api/accounts/<your-account-id>/workspaces/<your-workspace-id>';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_KEY = 'pnu_your_api_key_here';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_WORK_POOL = 'spcs-process';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;
EOF
```

### Step 7: Verify Agent is Online

```bash
# Check logs
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

You should see:

```text
🚀 Starting Prefect worker on Snowflake SPCS...
✅ Work Pool: spcs-process
✅ Starting Prefect worker...
   Running: prefect worker start --pool spcs-process

Worker started! Looking for work from work pool 'spcs-process'...
```

Then check **Prefect Cloud → Work Pools → spcs-process** to see your worker! 🎉

---

## 🔄 Updates (After Code Changes)

```bash
./deploy.sh --update
```

---

## 📋 Common Commands

### Local Testing

```bash
./test-local-container.sh --build  # Build and test
./test-local-container.sh --logs   # View logs
./test-local-container.sh --stop   # Stop
```

### Service Status

```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default
```

### Service Logs

```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

### Suspend/Resume

```bash
# Suspend (save costs)
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;" -c default

# Resume
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;" -c default
```

---

## 🔄 Development Workflow

1. **Edit code** → 2. **Test locally** → 3. **Deploy updates**

```bash
# Make changes to main.py or other files

# Test
./test-local-container.sh --build

# Deploy
./deploy.sh --update
```

---

## 🐛 Troubleshooting

### Connection Issues

```bash
snow connection list
snow connection test -c default
```

### Service Not Starting

```bash
# Check status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# Check logs
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

### Compute Pool Issues

```bash
snow sql -q "SHOW COMPUTE POOLS;" -c default
snow sql -q "DESCRIBE COMPUTE POOL E2E_FLOW_COMPUTE_POOL;" -c default
```

---

## 💡 Pro Tips

- **Always use `--update`** for subsequent deployments (preserves URL)
- **Test locally first** before deploying to Snowflake
- **Suspend when not in use** to save costs
- **Check logs** if something doesn't work
- **Monitor in Prefect Cloud** to see your worker status and flow runs

---

## 🔗 Prefect Cloud Quick Links

- **Dashboard**: [https://app.prefect.cloud](https://app.prefect.cloud)
- **Work Pools**: Check if your SPCS worker is online
- **Deployments**: Create flow deployments to run on your worker
- **Settings**: Get API URL and create API keys

---

## 📚 Full Documentation

- [README.md](../README.md) - Complete documentation
- [PREFECT_SETUP.md](PREFECT_SETUP.md) - Detailed Prefect configuration
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Comprehensive deployment guide
- [CREATE_WORK_POOL.md](CREATE_WORK_POOL.md) - Work pool creation guide
