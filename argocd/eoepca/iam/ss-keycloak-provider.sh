#!/usr/bin/bash
ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"
onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT
source .env 2>/dev/null
SECRET_NAME="keycloak-provider"
PROVIDER_CLIENT_SECRET="${2:-${PROVIDER_CLIENT_SECRET:-changeme}}"
CREDENTIALS="`cat <<EOF
{
  "client_id": "crossplane-keycloak-provider",
  "client_secret": "$PROVIDER_CLIENT_SECRET",
  "url": "https://iam-auth.rke2.deploybox.co.uk",
  "base_path": "",
  "realm": "eoepca"
}
EOF`"

sealFor() {
  local ns="$1"
  local outfile="$2"
  kubectl -n "${ns}" create secret generic "${SECRET_NAME}" \
    --from-literal="credentials=${CREDENTIALS}" \
    --dry-run=client -o yaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > "${outfile}"
}

sealFor "iam-management" "parts/ss-${SECRET_NAME}.yaml"
sealFor "iam" "parts/ss-${SECRET_NAME}-iam.yaml"