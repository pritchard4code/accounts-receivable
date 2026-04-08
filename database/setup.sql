-- =============================================================
-- Accounts Receivable Application - Database Setup Script
-- Run this as a PostgreSQL superuser (e.g. postgres)
-- Usage: psql -U postgres -f setup.sql
-- =============================================================

-- Create user if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'aruser') THEN
    CREATE USER aruser WITH PASSWORD 'arpassword';
  END IF;
END
$$;

-- Drop and recreate database
DROP DATABASE IF EXISTS accounts_receivable;
CREATE DATABASE accounts_receivable OWNER aruser;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE accounts_receivable TO aruser;

\echo 'Database created. Now run:'
\echo '  psql -U aruser -d accounts_receivable -f schema_and_data.sql'
