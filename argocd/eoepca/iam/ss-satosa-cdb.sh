#!/usr/bin/bash
ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"
onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT
source .env 2>/dev/null
SECRET_NAME="satosa-cdb"
SATOSA_CLIENT_SECRET="${1:-${SATOSA_CLIENT_SECRET:-`cat /dev/random|base64|tr -d "/=+-"|head -c 32`}}"
SATOSA_CLIENT_ID="${2:-${SATOSA_CLIENT_ID:-iam-keycloak}}"
SATOSA_REDIRECT_URI=${3:-${SATOSA_REDIRECT_URI:-https://develop-v2.eoepca.org/iam/auth/realms/eoepca/broker/satosa/endpoint}}
CDB="`cat <<EOF
{
  "$SATOSA_CLIENT_ID": {
    "response_types": ["code"],
    "client_id": "$SATOSA_CLIENT_ID",
    "client_secret": "$SATOSA_CLIENT_SECRET",
    "redirect_uris": [
      "$SATOSA_REDIRECT_URI"
    ]
  }
}
EOF`"

sealFor() {
  local ns="$1"
  local outfile="$2"
  kubectl -n "${ns}" create secret generic "${SECRET_NAME}" \
    --from-literal="cdb.json=${CDB}" \
    --from-literal="client_id=${SATOSA_CLIENT_ID}" \
    --from-literal="client_secret=${SATOSA_CLIENT_SECRET}" \
    --from-literal="redirect_uri=${SATOSA_REDIRECT_URI}" \
    --dry-run=client -o yaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > "${outfile}"
}

sealFor "iam" "parts/satosa/ss-${SECRET_NAME}.yaml"
