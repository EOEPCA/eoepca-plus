#!/bin/bash

set -euo pipefail

NAMESPACE="operations"
SECRET_NAME="loki-s3-credentials"

ACCESS_KEY="${AWS_ACCESS_KEY_ID:-${LOKI_S3_ACCESS_KEY_ID:-}}"
SECRET_KEY="${AWS_SECRET_ACCESS_KEY:-${LOKI_S3_SECRET_ACCESS_KEY:-}}"

if [[ -z "$ACCESS_KEY" ]]; then
  echo "Missing credentials: set AWS_ACCESS_KEY_ID or LOKI_S3_ACCESS_KEY_ID"
  exit 1
fi
if [[ -z "$SECRET_KEY" ]]; then
  echo "Missing credentials: set AWS_SECRET_ACCESS_KEY or LOKI_S3_SECRET_ACCESS_KEY"
  exit 1
fi

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: ${SECRET_NAME}
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "${ACCESS_KEY}"
  AWS_SECRET_ACCESS_KEY: "${SECRET_KEY}"
EOF

echo "Secret '${SECRET_NAME}' applied successfully to namespace '${NAMESPACE}'."
