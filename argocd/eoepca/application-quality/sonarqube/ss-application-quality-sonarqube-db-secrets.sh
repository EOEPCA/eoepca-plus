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

SECRET_NAME="application-quality-sonarqube-db-secrets"
NAMESPACE="application-quality-sonarqube"

USER_PASSWORD="${1:-${SONARQUBE_DB_USER_PASSWORD:-$(openssl rand -base64 24)}}"
ADMIN_PASSWORD="${2:-${SONARQUBE_DB_ADMIN_PASSWORD:-$(openssl rand -base64 24)}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="password=${USER_PASSWORD}" \
    --from-literal="postgres-password=${ADMIN_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > ss-${SECRET_NAME}.yaml
