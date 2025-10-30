-- Snowflake SPCS Setup SQL Script
-- Based on: https://github.com/sfc-gh-jkang/cortex-cost-app-spcs
-- Run these commands in Snowflake to set up the infrastructure

-- =============================================================================
-- STEP 1: Create Database
-- =============================================================================
CREATE DATABASE IF NOT EXISTS E2E_FLOW_DB
  COMMENT = 'Database for E2E Flow SPCS service';

USE DATABASE E2E_FLOW_DB;

-- =============================================================================
-- STEP 2: Create Schemas
-- =============================================================================

-- Schema for image repository
CREATE SCHEMA IF NOT EXISTS IMAGE_SCHEMA
  COMMENT = 'Schema for Docker image repository';

-- Schema for application resources (stages, service)
CREATE SCHEMA IF NOT EXISTS APP_SCHEMA
  COMMENT = 'Schema for application service and stages';

-- =============================================================================
-- STEP 3: Create Image Repository
-- =============================================================================
USE SCHEMA IMAGE_SCHEMA;

CREATE IMAGE REPOSITORY IF NOT EXISTS IMAGE_REPO
  COMMENT = 'Repository for E2E Flow Docker images';

-- Show repository URL (you'll need this for Docker)
SHOW IMAGE REPOSITORIES IN SCHEMA IMAGE_SCHEMA;

-- Get the repository URL
SELECT REPOSITORY_URL 
FROM E2E_FLOW_DB.INFORMATION_SCHEMA.IMAGE_REPOSITORIES 
WHERE REPOSITORY_SCHEMA = 'IMAGE_SCHEMA' 
  AND REPOSITORY_NAME = 'IMAGE_REPO';

-- =============================================================================
-- STEP 4: Create Application Stage
-- =============================================================================
USE SCHEMA APP_SCHEMA;

CREATE STAGE IF NOT EXISTS APP_STAGE
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Stage for service specification files';

-- =============================================================================
-- STEP 5: Create Compute Pool
-- =============================================================================
CREATE COMPUTE POOL IF NOT EXISTS E2E_FLOW_COMPUTE_POOL
  MIN_NODES = 1
  MAX_NODES = 3
  INSTANCE_FAMILY = CPU_X64_S
  AUTO_RESUME = TRUE
  AUTO_SUSPEND_SECS = 3600
  COMMENT = 'Compute pool for E2E Flow SPCS service';

-- Check compute pool status
DESCRIBE COMPUTE POOL E2E_FLOW_COMPUTE_POOL;
SHOW COMPUTE POOLS;

-- =============================================================================
-- STEP 6: Grant Necessary Privileges (if needed)
-- =============================================================================

-- Grant usage on compute pool (adjust role as needed)
-- GRANT USAGE ON COMPUTE POOL E2E_FLOW_COMPUTE_POOL TO ROLE <YOUR_ROLE>;

-- Grant privileges on database and schemas (adjust role as needed)
-- GRANT USAGE ON DATABASE E2E_FLOW_DB TO ROLE <YOUR_ROLE>;
-- GRANT USAGE ON SCHEMA E2E_FLOW_DB.IMAGE_SCHEMA TO ROLE <YOUR_ROLE>;
-- GRANT USAGE ON SCHEMA E2E_FLOW_DB.APP_SCHEMA TO ROLE <YOUR_ROLE>;
-- GRANT READ ON IMAGE REPOSITORY E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO TO ROLE <YOUR_ROLE>;
-- GRANT WRITE ON IMAGE REPOSITORY E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO TO ROLE <YOUR_ROLE>;

-- =============================================================================
-- DEPLOYMENT CHECKLIST
-- =============================================================================
-- At this point, you're ready to deploy! Use the deploy.sh script:
--
-- First deployment:
--   ./deploy.sh
--
-- Update existing service:
--   ./deploy.sh --update
--
-- =============================================================================
-- MONITORING & MANAGEMENT COMMANDS
-- =============================================================================

-- Check service status
-- SELECT SYSTEM$GET_SERVICE_STATUS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE');

-- View service logs (last 100 lines)
-- SELECT SYSTEM$GET_SERVICE_LOGS('E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE', '0', 'e2e-flow-container', 100);

-- Show service endpoints
-- SHOW ENDPOINTS IN SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE;

-- List all services
-- SHOW SERVICES IN SCHEMA E2E_FLOW_DB.APP_SCHEMA;

-- List images in repository
-- SHOW IMAGES IN IMAGE REPOSITORY E2E_FLOW_DB.IMAGE_SCHEMA.IMAGE_REPO;

-- Check files in stage
-- LIST @E2E_FLOW_DB.APP_SCHEMA.APP_STAGE;

-- =============================================================================
-- SERVICE MANAGEMENT COMMANDS
-- =============================================================================

-- Suspend service (stops billing but preserves service and endpoint)
-- ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE SUSPEND;

-- Resume service
-- ALTER SERVICE E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE RESUME;

-- Drop service (WARNING: This will delete the service and its endpoint URL)
-- DROP SERVICE IF EXISTS E2E_FLOW_DB.APP_SCHEMA.E2E_FLOW_SERVICE;

-- =============================================================================
-- CLEANUP COMMANDS (USE WITH CAUTION)
-- =============================================================================

-- Drop compute pool (must drop all services using it first)
-- DROP COMPUTE POOL IF EXISTS E2E_FLOW_COMPUTE_POOL;

-- Drop entire database (WARNING: This deletes everything)
-- DROP DATABASE IF EXISTS E2E_FLOW_DB;

