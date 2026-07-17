#!/bin/sh

# This is the entrypoint script for the SeaweedFS container.

# This binding will work both for Render and local Docker
BIND_IP="0.0.0.0" 

# Render automatically injects $PORT. Fall back to local variables if missing, so local Docker will still work.
S3_PORT=${PORT:-${WEED_S3_PORT:-8333}}
FILER_PORT=${WEED_FILER_PORT:-8888}
S3_DOMAIN="${WEED_S3_INTERNAL_DOMAIN:-localhost}"


echo "Binding IP  : $BIND_IP"
echo "S3 Domain   : $S3_DOMAIN"
echo "S3 Port     : $S3_PORT"
echo "Filer Port  : $FILER_PORT"

# Configure Postgres Filer Options for Seaweedfs metadata
FILER_ARGS="-filer=true -filer.port=$FILER_PORT"
if [ -n "$DATABASE_URL" ]; then
  # If running on Render, write a quick filer configuration to use Postgres
  mkdir -p /etc/seaweedfs
  echo "[postgres]\nenabled=true\nurl=\"$DATABASE_URL\"" > /etc/seaweedfs/filer.toml
  FILER_ARGS="$FILER_ARGS -filer.options=/etc/seaweedfs/filer.toml"
fi

# Boot SeaweedFS
exec weed server \
  -ip="$BIND_IP" \
  -dir="/data" \
  -s3=true \
  -s3.domainName="$S3_DOMAIN" \
  -s3.port="$S3_PORT" \
  $FILER_ARGS
