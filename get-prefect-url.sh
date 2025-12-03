#!/bin/bash

# Simple script to get and display Prefect API URL
# Uses UV for package management

set -e

echo "🔍 Getting Prefect Cloud API URL..."
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV not found."
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get API URL
API_URL=$(uv run prefect config view --show-sources 2>/dev/null | grep "PREFECT_API_URL" | awk -F"'" '{print $2}')

if [ -n "$API_URL" ] && [ "$API_URL" != "None" ] && [ "$API_URL" != "null" ]; then
    echo "✅ Found API URL:"
    echo "$API_URL"
    echo ""
    echo "📋 To export this URL:"
    echo "export PREFECT_API_URL=\"$API_URL\""
    echo ""
    
    # Ask to save to .env
    if [ -f .env ]; then
        read -p "Update .env file? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Remove old PREFECT_API_URL if exists
            sed -i.bak '/^PREFECT_API_URL=/d' .env 2>/dev/null || true
            echo "PREFECT_API_URL=$API_URL" >> .env
            echo "✅ Updated .env file"
        fi
    else
        read -p "Create .env file with this URL? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "PREFECT_API_URL=$API_URL" > .env
            echo "✅ Created .env file"
            echo ""
            echo "⚠️  Don't forget to add PREFECT_API_KEY to .env:"
            echo "echo 'PREFECT_API_KEY=pnu_your_key_here' >> .env"
        fi
    fi
else
    echo "⚠️  No Prefect API URL found."
    echo ""
    echo "Please log in first:"
    echo "  uv run prefect cloud login -k YOUR_API_KEY"
    echo ""
    echo "Or run the full setup script:"
    echo "  ./setup-prefect-env.sh"
    exit 1
fi











