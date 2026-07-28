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
IAM_CLIENT_ID="${3:-${IAM_CLIENT_ID:-somepw}}"
IAM_CLIENT_SECRET="${4:-${IAM_CLIENT_SECRET:-somepw}}"
OPERATON_DB_USERNAME="${5:-${OPERATON_DB_USERNAME:-somepw}}"
OPERATON_DB_PASSWORD="${6:-${OPERATON_DB_PASSWORD:-somepw}}"
EODAG__COP_DATASPACE__AUTH__CREDENTIALS__USERNAME="${7:-${EODAG__COP_DATASPACE__AUTH__CREDENTIALS__USERNAME:-somepw}}"
EODAG__COP_DATASPACE__AUTH__CREDENTIALS__PASSWORD="${8:-${EODAG__COP_DATASPACE__AUTH__CREDENTIALS__PASSWORD:-somepw}}"
EODAG__USGS__API__CREDENTIALS__USERNAME="${9:-${EODAG__USGS__API__CREDENTIALS__USERNAME:-somepw}}"
EODAG__USGS__API__CREDENTIALS__PASSWORD="${10:-${EODAG__USGS__API__CREDENTIALS__PASSWORD:-somepw}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="OPERATON_REST_USER=${OPERATON_REST_USER}" \
    --from-literal="OPERATON_REST_PASSWORD=${OPERATON_REST_PASSWORD}" \
    --from-literal="IAM_CLIENT_ID=${IAM_CLIENT_ID}" \
    --from-literal="IAM_CLIENT_SECRET=${IAM_CLIENT_SECRET}" \
    --from-literal="OPERATON_DB_USERNAME=${OPERATON_DB_USERNAME}" \
    --from-literal="OPERATON_DB_PASSWORD=${OPERATON_DB_PASSWORD}" \
    --from-literal="EODAG__COP_DATASPACE__AUTH__CREDENTIALS__USERNAME=${EODAG__COP_DATASPACE__AUTH__CREDENTIALS__USERNAME}" \
    --from-literal="EODAG__COP_DATASPACE__AUTH__CREDENTIALS__PASSWORD=${EODAG__COP_DATASPACE__AUTH__CREDENTIALS__PASSWORD}" \
    --from-literal="EODAG__USGS__API__CREDENTIALS__USERNAME=${EODAG__USGS__API__CREDENTIALS__USERNAME}" \
    --from-literal="EODAG__USGS__API__CREDENTIALS__PASSWORD=${EODAG__USGS__API__CREDENTIALS__PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
