# Creating a Work Pool in Prefect Cloud

Before deploying your Prefect agent to Snowflake SPCS, you need to create a work pool in Prefect Cloud.

## 🎯 What is a Work Pool?

A work pool is a bridge between Prefect Cloud and your infrastructure where work (flow runs) is executed. The agent running in your SPCS container will poll this work pool for flow runs to execute.

## 🌐 Method 1: Using Prefect Cloud UI

### Step 1: Log into Prefect Cloud

Go to [https://app.prefect.cloud](https://app.prefect.cloud)

### Step 2: Navigate to Work Pools

Click **Work Pools** in the left sidebar

### Step 3: Create Work Pool

1. Click **+ Create Work Pool** button
2. **Name**: Enter `spcs_worker` (or your preferred name)
3. **Type**: Select **Process** or **Agent-based**
4. Click **Create**

### Step 4: Note the Work Pool Name

You'll use this name when configuring your SPCS service:
```
spcs_worker
```

## 💻 Method 2: Using Prefect CLI (with UV)

### Create Work Pool via CLI

```bash
# Login first
uv run prefect cloud login -k pnu_your_api_key_here

# Create a work pool
uv run prefect work-pool create spcs_worker --type process

# Verify it was created
uv run prefect work-pool ls
```

### Output:
```
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Name        ┃ Type    ┃ Infrastructure ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ spcs_worker │ process │ None           │
└─────────────┴─────────┴────────────────┘
```

## 📋 Configuration in Snowflake SPCS

After creating the work pool, configure your SPCS service:

```sql
-- Set the work pool name
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_WORK_POOL = 'spcs_worker';

-- Also set API credentials if not already done
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_URL = 'https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_KEY = 'pnu_your_api_key_here';

-- Restart service
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;
```

## 🔍 Verify Agent Connection

### Check in Prefect Cloud

1. Go to **Work Pools** → **spcs_worker**
2. Click on the **Workers** tab
3. You should see your agent listed as **Online** 🟢

### Check Service Logs

```bash
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

You should see:
```
🚀 Starting Prefect agent on Snowflake SPCS...
✅ Connected to Prefect Cloud: https://api.prefect.cloud/api/accounts/...
✅ Work Pool: spcs_worker
✅ Starting Prefect agent...
   Running: prefect agent start --pool spcs_worker

Starting agent connected to https://api.prefect.cloud/api/accounts/...
Agent started! Looking for work from work pool 'spcs_worker'...
```

## 🚀 Creating a Deployment

Once your agent is running, create a deployment that targets this work pool:

### Using CLI

```bash
# Create a deployment
uv run prefect deployment build path/to/flow.py:flow_function \
  --name my-deployment \
  --pool spcs_worker \
  --apply

# Or if flow is already registered
uv run prefect deployment create \
  --flow my-flow \
  --name my-deployment \
  --pool spcs_worker
```

### Using Python

```python
from prefect import flow
from prefect.deployments import Deployment

@flow
def my_flow():
    print("Running on SPCS!")

if __name__ == "__main__":
    deployment = Deployment.build_from_flow(
        flow=my_flow,
        name="my-spcs-deployment",
        work_pool_name="spcs_worker",
    )
    deployment.apply()
```

## 📊 Work Pool Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Process** | Runs flows as local processes | Simple flows, SPCS containers |
| **Agent** | Legacy agent-based execution | Backward compatibility |
| **Kubernetes** | Runs flows in K8s pods | Cloud-native deployments |
| **Docker** | Runs flows in Docker containers | Containerized workflows |
| **ECS** | Runs flows on AWS ECS | AWS-specific deployments |

For SPCS, use **Process** type as the agent runs flows as subprocesses within the container.

## 🔧 Advanced Configuration

### Work Queue Concurrency

Set maximum concurrent flow runs:

```bash
uv run prefect work-pool set-concurrency-limit spcs_worker 10
```

### Work Pool Pausing

Temporarily pause the work pool:

```bash
# Pause (agents won't get work)
uv run prefect work-pool pause spcs_worker

# Resume
uv run prefect work-pool resume spcs_worker
```

### Viewing Work Pool Details

```bash
# Inspect work pool
uv run prefect work-pool inspect spcs_worker

# View work queues
uv run prefect work-queue ls --pool spcs_worker
```

## 📝 Environment Variable Reference

| Variable | Value | Description |
|----------|-------|-------------|
| `PREFECT_API_URL` | `https://api.prefect.cloud/api/accounts/...` | Your Prefect Cloud API endpoint |
| `PREFECT_API_KEY` | `pnu_...` | Your API key for authentication |
| `PREFECT_WORK_POOL` | `spcs_worker` | Name of the work pool to poll |

## 🐛 Troubleshooting

### "Work pool not found"

Make sure the work pool exists:
```bash
uv run prefect work-pool ls
```

Create it if missing:
```bash
uv run prefect work-pool create spcs_worker --type process
```

### Agent not showing in work pool

1. Check service logs for errors
2. Verify `PREFECT_WORK_POOL` matches the pool name exactly
3. Ensure agent is running (check service status)
4. Verify API credentials are correct

### No flows running

1. Ensure you have deployments targeting this work pool
2. Check deployment work pool name matches
3. Verify flows are scheduled or triggered
4. Check agent logs for errors

## 📚 Additional Resources

- [Prefect Work Pools Documentation](https://docs.prefect.io/latest/concepts/work-pools/)
- [Prefect Agents Guide](https://docs.prefect.io/latest/concepts/agents/)
- [Prefect Deployments](https://docs.prefect.io/latest/concepts/deployments/)

---

**Next Steps:**
1. ✅ Create work pool in Prefect Cloud
2. ✅ Deploy SPCS service with work pool configured
3. ✅ Verify agent is online
4. 🚀 Create and run deployments!



