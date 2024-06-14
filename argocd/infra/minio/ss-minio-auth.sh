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

SECRET_NAME="minio-auth"
NAMESPACE="infra"

ROOT_USER="${1:-${ROOT_USER:-eoepca}}"
ROOT_PASSWORD="${2:-${ROOT_PASSWORD:-changeme}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="rootUser=${ROOT_USER}" \
    --from-literal="rootPassword=${ROOT_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
# secretYaml | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > templates/ss-${SECRET_NAME}.yaml
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > ss-${SECRET_NAME}.yaml
