-- Per-database preparation. Run as a superuser while connected to the target database,
-- after create_roles.sql. Everything else (schemas, grants, extensions) is done by migrations
-- running as app_migrator.
--
--   psql -d <database> -f database/sql/roles/prepare_database.sql

SELECT format('ALTER DATABASE %I OWNER TO app_migrator', current_database())\gexec

ALTER SCHEMA public OWNER TO app_migrator;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database())\gexec
SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO app_runtime', current_database())\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO app_reporting', current_database())\gexec
