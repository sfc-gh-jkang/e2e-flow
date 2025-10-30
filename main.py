import os
import sys
import subprocess


def main():
    """
    Start a Prefect worker that connects to Prefect Cloud.
    
    Required environment variables:
    - PREFECT_API_URL: Your Prefect Cloud API URL
    - PREFECT_API_KEY: Your Prefect Cloud API key
    - PREFECT_WORK_POOL: Work pool name (default: spcs-process)
    """
    print("🚀 Starting Prefect worker on Snowflake SPCS...")
    
    # Check for required environment variables
    api_url = os.getenv("PREFECT_API_URL")
    api_key = os.getenv("PREFECT_API_KEY")
    work_pool = os.getenv("PREFECT_WORK_POOL", "spcs-process")
    
    if not api_url:
        print("❌ ERROR: PREFECT_API_URL environment variable is not set!")
        print("   Set it using: ALTER SERVICE ... SET PREFECT_API_URL='...'")
        sys.exit(1)
    
    if not api_key:
        print("❌ ERROR: PREFECT_API_KEY environment variable is not set!")
        print("   Set it using: ALTER SERVICE ... SET PREFECT_API_KEY='...'")
        sys.exit(1)
    
    print(f"✅ Connected to Prefect Cloud: {api_url}")
    print(f"✅ Work Pool: {work_pool}")
    print(f"✅ Starting Prefect worker...")
    
    # Start the Prefect worker
    # This will connect to Prefect Cloud and poll the work pool for work
    try:
        cmd = ["prefect", "worker", "start", "--pool", work_pool]
        print(f"   Running: {' '.join(cmd)}")
        print("")
        
        # Run the worker command
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down Prefect worker...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Prefect worker: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
