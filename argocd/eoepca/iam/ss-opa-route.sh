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

SECRET_NAME="opa-route"
NAMESPACE="iam-management"

OPA_CLIENT_SECRET="${1:-${OPA_CLIENT_SECRET:-changeme}}"
OPA_CLIENT_ID=${2:-${OPA_CLIENT_ID:-opa}}
test -z "$OPA_SESSION_SECRET" && OPA_SESSION_SECRET="`cat /dev/random|base64|tr -d "/=+-"|head -c 32`"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="client_id=${OPA_CLIENT_ID}" \
    --from-literal="client_secret=${OPA_CLIENT_SECRET}" \
    --from-literal="session.secret=${OPA_SESSION_SECRET}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
