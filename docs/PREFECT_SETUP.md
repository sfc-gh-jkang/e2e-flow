# Prefect Worker Setup on Snowflake SPCS

This guide explains how to configure and run a Prefect worker pool on Snowflake SPCS that connects to Prefect Cloud.

## 📋 Prerequisites

1. **Prefect Cloud Account**
   - Sign up at [https://app.prefect.cloud](https://app.prefect.cloud)
   - Create a workspace

2. **Prefect API Key**
   - In Prefect Cloud: Settings → API Keys → Create API Key
   - Save the key securely

3. **Workspace API URL**
   - Format: `https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>`
   - Find in Prefect Cloud: Settings → General → API URL

## 🔌 Network Requirements

The Prefect worker needs outbound HTTPS access to Prefect Cloud:

- **Protocol**: HTTPS (HTTP over SSL/TLS)
- **Port**: 443
- **Destination**: Prefect Cloud API (configured via `PREFECT_API_URL`)

✅ **Already configured** in `spcs-service-spec.yaml`:
```yaml
networkPolicyConfig:
  allowInternetEgress: true
```

This allows the container to make outbound connections to Prefect Cloud.

## 🚀 Deployment Steps

### Step 1: Deploy the Service

First, deploy the service to Snowflake SPCS:

```bash
./deploy.sh
```

### Step 2: Create Work Pool in Prefect Cloud

Before configuring the service, create a work pool in Prefect Cloud:

1. Log into [Prefect Cloud](https://app.prefect.cloud)
2. Go to **Work Pools**
3. Click **Create Work Pool**
4. Name it: `spcs-process` (or your preferred name)
5. Type: **Process**
6. Click **Create**

### Step 3: Configure Prefect Environment Variables

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
```

**Important**: Replace the placeholders with your actual values:
- `<your-account-id>`: Your Prefect Cloud account ID
- `<your-workspace-id>`: Your Prefect Cloud workspace ID
- `pnu_your_api_key_here`: Your actual Prefect API key
- `spcs-process`: Your work pool name (must match the pool created in Prefect Cloud)

### Step 4: Restart the Service

For the environment variables to take effect:

```sql
-- Suspend the service
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;

-- Resume with new configuration
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;
```

Or use the deployment script:

```bash
./deploy.sh --update
```

### Step 5: Verify Agent Connection

Check the service logs to confirm the worker connected:

```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

You should see:
```
🚀 Starting Prefect worker on Snowflake SPCS...
✅ Connected to Prefect Cloud: https://api.prefect.cloud/api/accounts/...
✅ Work Pool: spcs-process
✅ Starting Prefect worker...
   Running: prefect worker start --pool spcs-process

Starting worker connected to https://api.prefect.cloud/api/accounts/...
Worker started! Looking for work from work pool 'spcs-process'...
```

### Step 6: Check Prefect Cloud

Go to **Prefect Cloud → Work Pools → spcs-process** to see your worker online! 🎉

## 🔍 Monitoring Your Worker

### Check Worker Status in Prefect Cloud

1. Log into Prefect Cloud
2. Navigate to **Work Pools** → **spcs-process**
3. Click the **Workers** tab
4. You should see your SPCS worker connected 🟢

### View Worker Logs

```bash
# Real-time logs (last 100 lines)
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default

# More detailed logs (last 500 lines)
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 500);" -c default
```

### Check Service Status

```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default
```

## 🧪 Testing Locally

Before deploying to SPCS, test the Prefect worker locally:

1. **Create `.env` file** with your credentials:
   ```bash
   cat > .env << EOF
   PREFECT_API_URL=https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>
   PREFECT_API_KEY=pnu_your_api_key_here
   PYTHONUNBUFFERED=1
   EOF
   ```

2. **Run locally with Docker**:
   ```bash
   docker build --platform linux/amd64 -t e2e-flow:latest .
   docker run -p 8080:8080 --env-file .env e2e-flow:latest
   ```

3. **Verify connection** in Prefect Cloud (check Work Pools)

## 📝 Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PREFECT_API_URL` | Yes | Prefect Cloud API URL for your workspace |
| `PREFECT_API_KEY` | Yes | Your Prefect Cloud API key |
| `PREFECT_WORK_POOL` | No | Work pool name (default: `spcs-process`) |
| `PYTHONUNBUFFERED` | No | Ensures logs are immediately visible (default: 1) |

### Finding Your Prefect API URL

1. Log into Prefect Cloud
2. Go to **Settings** → **General**
3. Copy the **API URL**

Format: `https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>`

### Creating a Prefect API Key

1. Log into Prefect Cloud
2. Go to **Settings** → **API Keys**
3. Click **Create API Key**
4. Give it a name (e.g., "SPCS Worker")
5. Copy the key (starts with `pnu_`)
6. Save it securely - you won't be able to see it again!

## 🔧 Advanced Configuration

### Custom Work Pool

To use a different work pool name:

```sql
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_WORK_POOL = 'my-custom-pool';
```

**Note**: Make sure the work pool exists in Prefect Cloud before setting this!

### Multiple Workers (Scaling)

Increase worker instances in your service:

```sql
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  MIN_INSTANCES = 2
  MAX_INSTANCES = 5;
```

## 🐛 Troubleshooting

### Worker Not Connecting

**Check environment variables are set:**
```sql
SHOW PARAMETERS FOR SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE;
```

**Verify logs for errors:**
```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 200);" -c default
```

### Authentication Errors

If you see authentication errors in logs:

1. **Verify API key is correct**
2. **Check API key hasn't expired**
3. **Ensure API URL matches your workspace**

Recreate the API key in Prefect Cloud if needed.

### Network Connectivity Issues

**Verify internet egress is enabled:**
```bash
# Check service spec
snow sql -q "DESCRIBE SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE;" -c default
```

Should show: `allowInternetEgress: true`

**Test from inside container:**
```bash
# Get shell access (for debugging)
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 50);" -c default
```

### Worker Shows as Offline

**Common causes:**
1. Service is suspended
2. Environment variables not set
3. API key invalid or expired
4. Network egress blocked

**Solution:**
```sql
-- Resume service
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;

-- Check status
SELECT SYSTEM$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');
```

## 💰 Cost Optimization

### Suspend When Not In Use

```sql
-- Suspend worker (stops billing)
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;

-- Resume when needed
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;
```

### Auto-Scaling

The compute pool auto-suspends after 1 hour of inactivity (configured in `snowflake-setup.sql`).

## 📚 Additional Resources

- [Prefect Documentation](https://docs.prefect.io)
- [Prefect Cloud](https://app.prefect.cloud)
- [Prefect Workers Guide](https://docs.prefect.io/latest/concepts/work-pools/)
- [Snowflake SPCS Networking](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/additional-considerations-services-jobs#network-egress)

## 🎯 Quick Command Reference

```bash
# Deploy/Update service
./deploy.sh --update

# View logs
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default

# Check status
snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');" -c default

# Suspend/Resume
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;" -c default
snow sql -q "ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;" -c default
```

---

**🎉 Your Prefect worker is now running on Snowflake SPCS!**

