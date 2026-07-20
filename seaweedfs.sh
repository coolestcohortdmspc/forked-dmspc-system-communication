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

# Initialize default arguments for filer
FILER_ARGS="-filer=true -filer.port=$FILER_PORT"
S3_CONFIG_ARG=""

# Creates this filer.toml to store filer metadata (no postgres changes required)
if [ -n "$DATABASE_URL" ]; then
  mkdir -p /etc/seaweedfs
  cat <<EOF > /etc/seaweedfs/filer.toml
[postgres]
enabled=true
url="$DATABASE_URL"
EOF
  FILER_ARGS="$FILER_ARGS -filer.options=/etc/seaweedfs/filer.toml"
fi

# Handle S3 Credentials (will work locally & on render)
if [ -n "$WEED_S3_ACCESS_KEY" ] && [ -n "$WEED_S3_SECRET_KEY" ]; then
  mkdir -p /etc/seaweedfs
  cat <<EOF > /etc/seaweedfs/s3.json
{
  "identities": [
    {
      "name": "django_app",
      "credentials": [
        {
          "accessKey": "$WEED_S3_ACCESS_KEY",
          "secretKey": "$WEED_S3_SECRET_KEY"
        }
      ],
      "actions": ["Read", "Write", "List", "Tagging", "Admin"]
    }
  ]
}
EOF
  # Store the flag to pass s3 credentials into the final command
  S3_CONFIG_ARG="-s3.config=/etc/seaweedfs/s3.json"
fi

# Keeping these args below in case I need them later:
# -filer=true \
# -filer.port="$FILER_PORT"
# -s3 \

# Boot SeaweedFS
exec weed server \
  -ip="$BIND_IP" \
  -dir="/data" \
  -s3=true \
  -s3.domainName="$S3_DOMAIN" \
  -s3.port="$S3_PORT" \
  $S3_CONFIG_ARG \
  $FILER_ARGS