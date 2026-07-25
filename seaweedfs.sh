#!/bin/sh

# This is the entrypoint script for the SeaweedFS container.

# below tells the script to use .env vars
set -e

: "${WEED_DB_HOST:?WEED_DB_HOST is required}"
: "${WEED_DB_USER:?WEED_DB_USER is required}"
: "${WEED_DB_PASSWORD:?WEED_DB_PASSWORD is required}"
: "${WEED_DB_NAME:?WEED_DB_NAME is required}"

: "${WEED_S3_ACCESS_KEY:?WEED_S3_ACCESS_KEY is required}"
: "${WEED_S3_SECRET_KEY:?WEED_S3_SECRET_KEY is required}"

mkdir -p /etc/seaweedfs

envsubst < /filer.toml.template > /etc/seaweedfs/filer.toml
echo "Generated filer.toml"
cat /etc/seaweedfs/filer.toml

envsubst < /s3.json.template > /etc/seaweedfs/s3.json
echo "Generated s3.json"


exec weed server \
  -ip=0.0.0.0 \
  -dir=/data \
  -filer=true \
  -filer.port=8888 \
  -s3=true \
  -s3.port=8333 \
  -s3.config=/etc/seaweedfs/s3.json # \
  # -s3.externalUrl="$WEED_S3_PUBLIC_URL"

