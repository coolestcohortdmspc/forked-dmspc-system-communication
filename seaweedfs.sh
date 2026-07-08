#!/bin/sh

# This is the entrypoint script for the SeaweedFS container. It detects the environment (Render vs Local) and configures the S3 domain and ports accordingly.

# 1. Detect if running on Render vs Local
if [ -n "$RENDER" ] || [ "$APP_ENV" = "demo" ]; then
    echo "--- Demo Cloud Environment Detected ---"
    # Fallback syntax uses :- instead of ://
    S3_DOMAIN="${WEED_S3_DOMAIN:-https://system-communication-prototype.onrender.com/}" 
else
    echo "--- Local Development Environment Detected ---"
    S3_DOMAIN="localhost"
fi

# Bind to 0.0.0.0 so other containers in the docker network can connect
BIND_IP="0.0.0.0" 

# 2. Extract or fallback to configured ports
S3_PORT=${WEED_S3_PORT:-8333}
FILER_PORT=${WEED_FILER_PORT:-8888}

echo "Binding IP  : $BIND_IP"
echo "S3 Domain   : $S3_DOMAIN"
echo "S3 Port     : $S3_PORT"
echo "Filer Port  : $FILER_PORT"

# 3. Boot SeaweedFS 
exec weed server \
  -ip="$BIND_IP" \
  -dir="/data" \
  -s3 \
  -s3.domainName="$S3_DOMAIN" \
  -s3.port="$S3_PORT" \
  -filer=true \
  -filer.port="$FILER_PORT"
