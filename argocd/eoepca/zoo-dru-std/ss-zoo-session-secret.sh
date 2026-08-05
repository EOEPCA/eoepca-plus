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

SECRET_NAME="zoo-session-secret"
NAMESPACE="iam-management"

# Used to encrypt the APISIX openid-connect plugin's session cookie.
SESSION_SECRET="${1:-${ZOO_SESSION_SECRET:-`cat /dev/random|base64|tr -d "/=+-"|head -c 32`}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="session.secret=${SESSION_SECRET}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/secrets/ss-${SECRET_NAME}.yaml
