#!/usr/bin/bash

ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"

onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT

# Optional local .env file for secret values as env vars
source .env 2>/dev/null

SECRET_NAME="keycloak-admin"
NAMESPACE="iam"

MASTER_ADMIN_USERNAME="${MASTER_ADMIN_USERNAME:-admin}"
MASTER_ADMIN_PASSWORD="${1:-${MASTER_ADMIN_PASSWORD:-`cat /dev/random|base64|tr -d "/=+-"|head -c 32`}}"
MASTER_ADMIN_CLIENT_ID="${MASTER_ADMIN_CLIENT_ID:-admin_client}"
MASTER_ADMIN_CLIENT_SECRET="${2:-${MASTER_ADMIN_CLIENT_SECRET:-`cat /dev/random|base64|tr -d "/=+-"|head -c 32`}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="client-id=${MASTER_ADMIN_CLIENT_ID}" \
    --from-literal="client-secret=${MASTER_ADMIN_CLIENT_SECRET}" \
    --from-literal="username=${MASTER_ADMIN_USERNAME}" \
    --from-literal="password=${MASTER_ADMIN_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
