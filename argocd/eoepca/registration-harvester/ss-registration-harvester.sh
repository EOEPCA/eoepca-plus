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

SECRET_NAME="registration-harvester-secret"
NAMESPACE="registration-harvester-api"

OPERATON_REST_USER="${1:-${OPERATON_REST_USER:-someuser}}"
OPERATON_REST_PASSWORD="${2:-${OPERATON_REST_PASSWORD:-somepw}}"
M2M_USER="${3:-${M2M_USER:-someuser}}"
M2M_PASSWORD="${4:-${M2M_PASSWORD:-somepw}}"
CDSE_USER="${5:-${CDSE_USER:-someuser}}"
CDSE_PASSWORD="${6:-${CDSE_PASSWORD:-somepw}}"
IAM_CLIENT_ID="${7:-${IAM_CLIENT_ID:-somepw}}"
IAM_CLIENT_SECRET="${8:-${IAM_CLIENT_SECRET:-somepw}}"
OPERATON_DB_USERNAME="${9:-${OPERATON_DB_USERNAME:-somepw}}"
OPERATON_DB_PASSWORD="${10:-${OPERATON_DB_PASSWORD:-somepw}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="OPERATON_REST_USER=${OPERATON_REST_USER}" \
    --from-literal="OPERATON_REST_PASSWORD=${OPERATON_REST_PASSWORD}" \
    --from-literal="M2M_USER=${M2M_USER}" \
    --from-literal="M2M_PASSWORD=${M2M_PASSWORD}" \
    --from-literal="CDSE_USER=${CDSE_USER}" \
    --from-literal="CDSE_PASSWORD=${CDSE_PASSWORD}" \
    --from-literal="IAM_CLIENT_ID=${IAM_CLIENT_ID}" \
    --from-literal="IAM_CLIENT_SECRET=${IAM_CLIENT_SECRET}" \
    --from-literal="OPERATON_DB_USERNAME=${OPERATON_DB_USERNAME}" \
    --from-literal="OPERATON_DB_PASSWORD=${OPERATON_DB_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
