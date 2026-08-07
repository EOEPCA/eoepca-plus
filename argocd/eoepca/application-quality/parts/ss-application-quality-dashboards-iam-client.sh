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

SECRET_NAME="application-quality-dashboards-iam-client"
NAMESPACE="iam-management"

APPLICATION_QUALITY_DASHBOARDS_CLIENT_SECRET="${1:-${APPLICATION_QUALITY_DASHBOARDS_CLIENT_SECRET:-changeme}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="client_secret=${APPLICATION_QUALITY_DASHBOARDS_CLIENT_SECRET}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > ss-${SECRET_NAME}.yaml
