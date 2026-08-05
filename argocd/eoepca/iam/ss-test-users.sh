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

SECRET_NAME="test-users"
NAMESPACE="iam-management"

ALICE_PASSWORD="${1:-${ALICE_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)}}"
BOB_PASSWORD="${2:-${BOB_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)}}"
ERIC_PASSWORD="${3:-${ERIC_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="alice-password=${ALICE_PASSWORD}" \
    --from-literal="bob-password=${BOB_PASSWORD}" \
    --from-literal="eric-password=${ERIC_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
