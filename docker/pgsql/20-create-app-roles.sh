#!/bin/sh
# Creates the application roles and prepares the development and test databases
# (original docker/pgsql/20-create-app-roles.sh). Runs once, on the first start of an empty
# data volume (docker-entrypoint-initdb.d). SQL files: db/sql/roles/ mounted at /opt/app-sql.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -v migrator_password="$APP_DB_MIGRATOR_PASSWORD" \
    -v runtime_password="$APP_DB_RUNTIME_PASSWORD" \
    -v reporting_password="$APP_DB_REPORTING_PASSWORD" \
    -f /opt/app-sql/roles/create_roles.sql

# The test database is recreated by the test session (tests/conftest.py) when --reuse-db is not
# given; preparing it here lets `pytest --reuse-db` start immediately.
for database in "$POSTGRES_DB" "${APP_DB_TEST_DATABASE:-test_ninefruits}"; do
    if [ "$database" != "$POSTGRES_DB" ]; then
        createdb --username "$POSTGRES_USER" "$database"
    fi
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" \
        -f /opt/app-sql/roles/prepare_database.sql
done
