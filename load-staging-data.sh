#!/usr/bin/env bash

set -euo pipefail

echo "========================================"
echo " Loading staging database into local DB "
echo "========================================"
echo

#
# Verify required environment variable
#
if [ -z "${DEMO_DATABASE_URL:-}" ]; then
    echo "ERROR: DEMO_DATABASE_URL is not defined."
    exit 1
fi

#
# Local database connection
#
LOCAL_DB_URL="postgres://ngradar_website:ngradar_website@postgres:5432/localdev"

#
# Wait until local postgres is accepting connections
#
echo "Waiting for local PostgreSQL..."

until pg_isready \
    -h postgres \
    -U ngradar_website \
    -d localdev
do
    sleep 2
done

echo "Local PostgreSQL is ready."
echo

#
# Ask for confirmation
#
echo "WARNING"
echo "This will completely overwrite your LOCAL database."
echo

read -p "Continue? (y/N): " ANSWER

if [[ "$ANSWER" != "y" && "$ANSWER" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

echo
echo "Dumping staging database..."

pg_dump \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    "$DEMO_DATABASE_URL" \
    > /tmp/staging.sql

echo "Dump complete."
echo

echo "Restoring into local database..."

psql "$LOCAL_DB_URL" < /tmp/staging.sql

echo

rm /tmp/staging.sql

echo "========================================"
echo " Local database successfully refreshed."
echo "========================================"