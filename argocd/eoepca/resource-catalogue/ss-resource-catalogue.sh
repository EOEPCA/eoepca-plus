#!/usr/bin/env bash

ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"

onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT

# Optional local .env file for secret values as env vars
source .env 2>/dev/null

SECRET_NAME="resource-catalogue-secret"
NAMESPACE="rm"

EOEPCA_USERNAME="${1:-${EOEPCA_USERNAME:-someusername}}"
EOEPCA_PASSWORD="${2:-${EOEPCA_PASSWORD:-somesecret}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="username=${EOEPCA_USERNAME}" \
    --from-literal="password=${EOEPCA_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
