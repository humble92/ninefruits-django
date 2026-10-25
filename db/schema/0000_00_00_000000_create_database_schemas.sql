CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS audit;

CREATE SCHEMA IF NOT EXISTS reporting;

CREATE SCHEMA IF NOT EXISTS util;

GRANT USAGE ON SCHEMA public TO "app_runtime";

GRANT USAGE ON SCHEMA util TO "app_runtime", "app_reporting";

GRANT USAGE ON SCHEMA audit TO "app_runtime";

GRANT USAGE ON SCHEMA reporting TO "app_runtime", "app_reporting";

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "app_runtime";

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "app_runtime";

ALTER DEFAULT PRIVILEGES IN SCHEMA reporting GRANT SELECT ON TABLES TO "app_runtime", "app_reporting";

ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT ON TABLES TO "app_runtime";

-- @apply functions/session_context.sql

-- @apply functions/i18n.sql

