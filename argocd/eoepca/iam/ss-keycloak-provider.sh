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

SECRET_NAME="keycloak-provider"
NAMESPACE="iam-management"

PROVIDER_CLIENT_SECRET="${2:-${PROVIDER_CLIENT_SECRET:-changeme}}"
CREDENTIALS="`cat <<EOF
{
  "client_id": "crossplane-keycloak-provider",
  "client_secret": "$PROVIDER_CLIENT_SECRET",
  "url": "https://iam-auth.develop.eoepca.org",
  "base_path": "",
  "realm": "eoepca"
}
EOF`"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="credentials=${CREDENTIALS}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
