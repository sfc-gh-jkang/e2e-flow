# Prefect Authentication Methods

This guide explains how Prefect authentication works in containers and why you **don't need** to run `prefect cloud login`.

## ✅ **Current Approach (Recommended)**

### How It Works

The Prefect SDK **automatically authenticates** using environment variables:

```python
# No login command needed!
# Prefect SDK reads these automatically:
import os
from prefect.worker.serve import serve

# These env vars are all you need:
# - PREFECT_API_URL
# - PREFECT_API_KEY

serve()  # Already authenticated!
```

### Why This Works

When you set these environment variables, the Prefect SDK:

1. Reads `PREFECT_API_URL` to know where to connect
2. Reads `PREFECT_API_KEY` for authentication
3. Automatically includes the API key in all API requests
4. No separate login step needed!

### Configuration

**In Snowflake SPCS:**

```sql
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_URL = 'https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_KEY = 'pnu_your_api_key_here';
```

**Locally with Docker:**

```bash
docker run -p 8080:8080 \
  -e PREFECT_API_URL="https://api.prefect.cloud/api/accounts/..." \
  -e PREFECT_API_KEY="pnu_your_key" \
  e2e-flow:latest
```

**With docker-compose:**

```bash
# Create .env file
cat > .env << EOF
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/<id>/workspaces/<id>
PREFECT_API_KEY=pnu_your_api_key_here
EOF

# Run
docker-compose up
```

## 🔄 **Alternative: Using Entrypoint Script**

If you want to run `prefect cloud login` at container startup, I've created an `entrypoint.sh` script.

### Enable the Entrypoint

**Uncomment in Dockerfile:**

```dockerfile
# Use entrypoint script for any pre-startup commands
ENTRYPOINT ["./entrypoint.sh"]
```

### Usage

Set an additional environment variable:

```sql
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_CLOUD_LOGIN = 'true';
```

### What It Does

The entrypoint script:

1. Validates environment variables
2. Optionally runs `prefect cloud login -k $PREFECT_API_KEY`
3. Starts your application

**But note**: This is **not necessary** because the SDK already handles authentication!

## ❌ **Why NOT in Dockerfile Build**

You **cannot** use `.env` files during `docker build`:

```dockerfile
# ❌ THIS DOESN'T WORK - .env not available during build
RUN prefect cloud login -k $PREFECT_API_KEY
```

**Why?**

- `.env` files are only available at **runtime** (when container runs)
- Docker `RUN` commands execute during **build time**
- Build-time secrets would be baked into the image (security risk!)

## 🔐 **Security Best Practices**

### ✅ **DO**

```bash
# Environment variables at runtime
docker run -e PREFECT_API_KEY="pnu_..." e2e-flow:latest

# Or use .env file (not committed to git)
docker run --env-file .env e2e-flow:latest

# Or Snowflake ALTER SERVICE commands
ALTER SERVICE ... SET PREFECT_API_KEY = '...';
```

### ❌ **DON'T**

```dockerfile
# Never hardcode secrets in Dockerfile
ENV PREFECT_API_KEY="pnu_my_secret_key"  # BAD!

# Never bake secrets during build
RUN prefect cloud login -k "pnu_my_secret_key"  # BAD!
```

## 🧪 **Testing Authentication**

### Test Locally

```bash
# Create .env file
cat > .env << EOF
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/<id>/workspaces/<id>
PREFECT_API_KEY=pnu_your_api_key_here
EOF

# Run container
docker run -p 8080:8080 --env-file .env e2e-flow:latest
```

### Verify in Logs

You should see:

```text
🚀 Starting Prefect worker on Snowflake SPCS...
✅ Connected to Prefect Cloud: https://api.prefect.cloud/api/accounts/...
✅ Worker starting on port 8080...
```

### Check Prefect Cloud

Go to **Prefect Cloud → Work Pools** and verify your worker appears online.

## 📊 **Comparison**

| Method | Pros | Cons | Recommended? |
|--------|------|------|--------------|
| **Environment Variables** | Simple, secure, automatic | None | ✅ **YES** |
| **Entrypoint Script** | Flexible, can run pre-commands | Extra complexity | 🟡 Optional |
| **Dockerfile RUN** | N/A | Doesn't work, security risk | ❌ **NO** |

## 🎯 **Recommended Setup**

**Your current setup is already optimal!**

1. **Set environment variables** (in Snowflake or locally)
2. **Prefect SDK authenticates automatically**
3. **No login command needed**
4. **Secure and simple**

## 🔍 **Troubleshooting**

### "Authentication failed"

```bash
# Check env vars are set
docker exec e2e-flow-local env | grep PREFECT

# Should show:
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/...
PREFECT_API_KEY=pnu_...
```

### "Worker not showing in Prefect Cloud"

```bash
# Check logs
docker logs e2e-flow-local

# Or in SPCS
snow sql -q "SELECT SYSTEM\$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);" -c default
```

### "Invalid API key"

- Verify the key starts with `pnu_`
- Check it hasn't expired
- Regenerate in Prefect Cloud: Settings → API Keys

## 📚 **References**

- [Prefect Cloud API Keys](https://docs.prefect.io/latest/cloud/users/api-keys/)
- [Prefect Environment Variables](https://docs.prefect.io/latest/concepts/settings/)
- [Docker Environment Variables](https://docs.docker.com/compose/environment-variables/)

## 💡 **Summary**

**You don't need to run `prefect cloud login` in Docker containers!**

Just set these environment variables:

- `PREFECT_API_URL`
- `PREFECT_API_KEY`

The Prefect SDK handles authentication automatically. 🎉

---

**Current setup is already correct and secure!** ✅
