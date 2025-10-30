# How to Get Your PREFECT_API_URL via CLI

## 🎯 Quick Answer

**With UV (recommended for this project):**

```bash
# Get your current API URL
uv run prefect config view --show-sources | grep PREFECT_API_URL

# Or view all config
uv run prefect config view
```

**Without UV (standard Prefect):**

```bash
prefect config view | grep PREFECT_API_URL
```

## 📋 Step-by-Step Methods

### Method 1: View Current Configuration (UV)

If you're already logged in:

```bash
# Show current Prefect configuration
uv run prefect config view

# Filter for API URL
uv run prefect config view --show-sources | grep PREFECT_API_URL

# Extract just the URL value
uv run prefect config view --show-sources | grep "PREFECT_API_URL" | awk -F"'" '{print $2}'
```

**Output:**

```text
PREFECT_API_URL='https://api.prefect.cloud/api/accounts/abc-123/workspaces/xyz-456'
```

### Method 2: Get Workspace Info (UV)

```bash
# Login first (if not already)
uv run prefect cloud login

# Get current workspace info
uv run prefect cloud workspace ls

# Get current workspace details
uv run prefect cloud workspace get
```

**Output:**

```json
{
  "account_handle": "my-account",
  "workspace_handle": "my-workspace",
  "api_url": "https://api.prefect.cloud/api/accounts/abc-123/workspaces/xyz-456"
}
```

### Method 3: Extract from JSON (UV)

```bash
# Get workspace info as JSON and extract URL
uv run prefect cloud workspace get --json | jq -r '.api_url'

# Or using Python with UV
uv run python -c "from prefect.settings import PREFECT_API_URL; print(PREFECT_API_URL.value())"
```

### Method 4: Login Interactively (Gets URL Automatically) (UV)

```bash
# Interactive login - shows your workspaces
uv run prefect cloud login

# Select your workspace
# The API URL will be displayed and automatically configured
```

**Output:**

```text
? Which workspace would you like to use?
  ❯ my-account/my-workspace
    https://api.prefect.cloud/api/accounts/abc-123/workspaces/xyz-456
```

### Method 5: List All Workspaces (UV)

```bash
# Login with API key
uv run prefect cloud login -k pnu_your_api_key_here

# List all available workspaces
uv run prefect cloud workspace ls

# Switch to specific workspace (sets API URL)
uv run prefect cloud workspace set --workspace "my-account/my-workspace"

# Verify the URL was set
uv run prefect config view | grep PREFECT_API_URL
```

## 🔧 Complete Setup Script (UV)

Here's a script to get and export your Prefect API URL:

```bash
#!/bin/bash

# get-prefect-url.sh
echo "🔍 Getting Prefect Cloud API URL..."

# Method 1: If already logged in
API_URL=$(uv run prefect config view --show-sources 2>/dev/null | grep "PREFECT_API_URL" | awk -F"'" '{print $2}')

if [ -n "$API_URL" ] && [ "$API_URL" != "None" ]; then
    echo "✅ Found API URL from existing configuration:"
    echo "$API_URL"
else
    echo "⚠️  Not logged in. Please log in first:"
    echo "   uv run prefect cloud login -k YOUR_API_KEY"
    exit 1
fi

# Export for use in shell
echo ""
echo "📋 To export this URL:"
echo "export PREFECT_API_URL=\"$API_URL\""

# Save to .env file
echo ""
read -p "Save to .env file? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "PREFECT_API_URL=$API_URL" >> .env
    echo "✅ Saved to .env file"
fi
```

## 🚀 Quick Commands for Your Project (UV)

### Setup for Local Development

```bash
# 1. Login to Prefect Cloud
uv run prefect cloud login -k pnu_your_api_key_here

# 2. Get the API URL
PREFECT_API_URL=$(uv run prefect config view --show-sources | grep "PREFECT_API_URL" | awk -F"'" '{print $2}')

# 3. Create .env file
cat > .env << EOF
PREFECT_API_URL=$PREFECT_API_URL
PREFECT_API_KEY=pnu_your_api_key_here
EOF

echo "✅ .env file created!"
```

### Setup for Snowflake SPCS (UV)

```bash
# 1. Get your API URL
PREFECT_API_URL=$(uv run prefect config view --show-sources | grep "PREFECT_API_URL" | awk -F"'" '{print $2}')

# 2. Set in Snowflake service
snow sql -c default << EOF
ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_URL = '$PREFECT_API_URL';

ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SET
  PREFECT_API_KEY = 'pnu_your_api_key_here';
EOF

echo "✅ Prefect credentials set in Snowflake!"
```

## 🌐 Alternative: Get from Prefect Cloud UI

If you prefer the web interface:

1. **Log into Prefect Cloud**: <https://app.prefect.cloud>
2. **Go to Settings** → **General**
3. **Copy the API URL** shown there

Format: `https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>`

## 🔐 Get API Key Too

While you're at it, get your API key:

```bash
# Login interactively (creates a new API key if needed)
prefect cloud login

# List existing API keys (requires web UI)
# Go to: https://app.prefect.cloud → Settings → API Keys
```

Or create via CLI:

```bash
# Login first
prefect cloud login

# Your API key is stored locally at:
cat ~/.prefect/profiles.toml
```

## 📝 Environment File Template

Create this script to set up your environment:

```bash
#!/bin/bash
# setup-prefect-env.sh

echo "🔧 Prefect Environment Setup"
echo ""

# Check if prefect is installed
if ! command -v prefect &> /dev/null; then
    echo "❌ Prefect CLI not found. Install with:"
    echo "   pip install prefect"
    exit 1
fi

# Get API URL
echo "📡 Getting Prefect API URL..."
API_URL=$(prefect config get PREFECT_API_URL 2>/dev/null)

if [ -z "$API_URL" ] || [ "$API_URL" = "None" ]; then
    echo "⚠️  Not logged in to Prefect Cloud"
    echo ""
    read -p "Enter your Prefect API key (starts with pnu_): " API_KEY

    # Login
    prefect cloud login -k "$API_KEY"

    # Get URL again
    API_URL=$(prefect config get PREFECT_API_URL)
else
    echo "✅ Found API URL"
    read -p "Enter your Prefect API key (starts with pnu_): " API_KEY
fi

# Create .env file
cat > .env << EOF
# Prefect Cloud Configuration
PREFECT_API_URL=$API_URL
PREFECT_API_KEY=$API_KEY

# Application Settings
PYTHONUNBUFFERED=1
EOF

echo ""
echo "✅ Created .env file with:"
echo "   PREFECT_API_URL=$API_URL"
echo "   PREFECT_API_KEY=***"
echo ""
echo "🚀 Ready to run:"
echo "   docker-compose up"
```

## 🧪 Verify Your Configuration

```bash
# Test that everything is configured correctly
prefect config view

# Test connection to Prefect Cloud
prefect cloud workspace ls

# Verify you can see your workspace
echo "Current workspace:"
prefect cloud workspace get
```

## 💡 Pro Tips

### Save as Environment Variable

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export PREFECT_API_URL=$(prefect config get PREFECT_API_URL)
export PREFECT_API_KEY="pnu_your_key_here"
```

### Use in Scripts

```bash
#!/bin/bash
# Automatically get API URL in scripts
if [ -z "$PREFECT_API_URL" ]; then
    export PREFECT_API_URL=$(prefect config get PREFECT_API_URL)
fi

echo "Using Prefect at: $PREFECT_API_URL"
```

### Docker Compose with Automatic Detection

```yaml
# docker-compose.yml
services:
  e2e-flow:
    environment:
      - PREFECT_API_URL=${PREFECT_API_URL:-$(shell prefect config get PREFECT_API_URL)}
      - PREFECT_API_KEY=${PREFECT_API_KEY}
```

## 🔍 Troubleshooting

### "Command not found: prefect"

```bash
# Install Prefect
pip install prefect

# Or with uv
uv pip install prefect
```

### "Not authenticated"

```bash
# Login with API key
prefect cloud login -k pnu_your_api_key_here
```

### "No workspace selected"

```bash
# List workspaces
prefect cloud workspace ls

# Select workspace
prefect cloud workspace set --workspace "account/workspace"
```

## 📚 Related Commands

```bash
# View all Prefect settings
prefect config view --show-defaults

# View specific setting
prefect config get PREFECT_API_URL

# Set a config value
prefect config set PREFECT_API_URL="https://..."

# Unset a config value
prefect config unset PREFECT_API_URL

# Show profile information
prefect profile ls
prefect profile inspect
```

---

## 🎯 Quick Reference (UV)

```bash
# Get API URL (if logged in)
uv run prefect config view | grep PREFECT_API_URL

# Or extract just the value
uv run prefect config view --show-sources | grep "PREFECT_API_URL" | awk -F"'" '{print $2}'

# Login and get URL
uv run prefect cloud login -k pnu_your_key
uv run prefect config view | grep PREFECT_API_URL

# Export to environment
export PREFECT_API_URL=$(uv run prefect config view --show-sources | grep "PREFECT_API_URL" | awk -F"'" '{print $2}')

# Save to .env
echo "PREFECT_API_URL=$(uv run prefect config view --show-sources | grep "PREFECT_API_URL" | awk -F"'" '{print $2}')" >> .env
```

---

**Quick start**: Just run `uv run prefect cloud login` and it will show you your workspaces and API URLs! 🚀
