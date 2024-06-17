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

SECRET_NAME="data-access-secrets"
NAMESPACE="rm"

CREODIAS_EODATA_S3_ACCESS_KEY="${1:-${CREODIAS_EODATA_S3_ACCESS_KEY:-eoepca}}"
CREODIAS_EODATA_S3_ACCESS_SECRET="${2:-${CREODIAS_EODATA_S3_ACCESS_SECRET:-changeme}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="CREODIAS_EODATA_S3_ACCESS_KEY=${CREODIAS_EODATA_S3_ACCESS_KEY}" \
    --from-literal="CREODIAS_EODATA_S3_ACCESS_SECRET=${CREODIAS_EODATA_S3_ACCESS_SECRET}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml