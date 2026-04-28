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

SECRET_NAME="zoo-workflow-env"
NAMESPACE="zoo"

STAGEIN_AWS_ACCESS_KEY_ID="${1:-${STAGEIN_AWS_ACCESS_KEY_ID:-someclient}}"
STAGEIN_AWS_SECRET_ACCESS_KEY="${2:-${STAGEIN_AWS_SECRET_ACCESS_KEY:-somesecret}}"
STAGEIN_AWS_SERVICEURL="${3:-${STAGEIN_AWS_SERVICEURL:-http://eodata.cloudferro.com}}"
STAGEIN_AWS_REGION="${4:-${STAGEIN_AWS_REGION:-WAW3-2}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="STAGEIN_AWS_ACCESS_KEY_ID=${STAGEIN_AWS_ACCESS_KEY_ID}" \
    --from-literal="STAGEIN_AWS_SECRET_ACCESS_KEY=${STAGEIN_AWS_SECRET_ACCESS_KEY}" \
    --from-literal="STAGEIN_AWS_SERVICEURL=${STAGEIN_AWS_SERVICEURL}" \
    --from-literal="STAGEIN_AWS_REGION=${STAGEIN_AWS_REGION}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
