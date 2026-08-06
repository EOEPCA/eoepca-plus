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

SECRET_NAME="eoepca-realm"
NAMESPACE="iam"

SMTP_PASSWORD="${1:-${SMTP_PASSWORD:-changeme}}"
GITHUB_CLIENT_SECRET="${2:-${GITHUB_CLIENT_SECRET:-changeme}}"
#EOIAM_CLIENT_SECRET="${3:-${EOIAM_CLIENT_SECRET:-changeme}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="smtp_password=${SMTP_PASSWORD}" \
    --from-literal="github_client_secret=${GITHUB_CLIENT_SECRET}" \
    --dry-run=client -o yaml
}
# TODO: Add when needed:
#    --from-literal="eoiam_client_secret=${EOIAM_CLIENT_SECRET}" \

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
