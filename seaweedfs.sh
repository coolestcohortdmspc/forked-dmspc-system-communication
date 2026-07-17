#!/bin/sh

# This is the entrypoint script for the SeaweedFS container.

S3_DOMAIN="${WEED_S3_DOMAIN}" 

# Bind to 0.0.0.0 so other containers in the docker network can connect
# TODO: Will this still work if hosted on Render?
# Or should I let an env var handle assigning this?
BIND_IP="0.0.0.0" 

# 2. Extract or fallback to configured ports
S3_PORT=${WEED_S3_PORT:-8333}
FILER_PORT=${WEED_FILER_PORT:-8888}

echo "Binding IP  : $BIND_IP"
echo "S3 Domain   : $S3_DOMAIN"
echo "S3 Port     : $S3_PORT"
echo "Filer Port  : $FILER_PORT"

# 3. Boot SeaweedFS 
# TODO: Will I need to remove the bind_ip command below for render?
exec weed server \
  -ip="$BIND_IP" \
  -dir="/data" \
  -s3=true \
  -s3.domainName="$S3_DOMAIN" \
  -s3.port="$S3_PORT" \
  -filer=true \
  -filer.port="$FILER_PORT"
