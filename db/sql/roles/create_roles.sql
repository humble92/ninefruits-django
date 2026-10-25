-- Cluster-level application roles. Run once per PostgreSQL cluster as a superuser.
--
--   psql -v migrator_password=... -v runtime_password=... -v reporting_password=... \
--        -f database/sql/roles/create_roles.sql
--
-- app_migrator  : owns schemas and tables, runs migrations only.
-- app_runtime   : used by the application. Not a table owner, so row level security applies.
-- app_reporting : read-only access to the reporting schema.

SELECT format('CREATE ROLE app_migrator LOGIN PASSWORD %L', :'migrator_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_migrator')\gexec

SELECT format('CREATE ROLE app_runtime LOGIN PASSWORD %L', :'runtime_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_runtime')\gexec

SELECT format('CREATE ROLE app_reporting LOGIN PASSWORD %L', :'reporting_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_reporting')\gexec

ALTER ROLE app_migrator NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB;
ALTER ROLE app_runtime NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB;
ALTER ROLE app_reporting NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB;
