#!/usr/bin/bash

ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"

onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT

SECRET_NAME="openid-connect"
NAMESPACE="gitlab"

# Parameters from env
source .env 2>/dev/null  # Optional local .env file for secret values as env vars
DOMAIN=${DOMAIN:-develop-v2.eoepca.org}
MLOPS_GITLAB_CLIENT_ID=${MLOPS_GITLAB_CLIENT_ID:-mlopsbb-gitlab}
MLOPS_GITLAB_CLIENT_SECRET=${MLOPS_GITLAB_CLIENT_SECRET:-changeme}

providerYaml() {
  cat <<EOF
name: openid_connect
label: EOEPCA
icon: "https://eoepca.readthedocs.io/img/favicon.ico"
args:
  name: openid_connect
  scope: ["openid", "profile", "email"]
  response_type: "code"
  issuer: "https://${DOMAIN}/iam/auth/realms/eoepca"
  client_auth_method: "query"
  discovery: true
  uid_field: "preferred_username"
  pkce: true
  client_options:
    identifier: "${MLOPS_GITLAB_CLIENT_ID}"
    secret: "${MLOPS_GITLAB_CLIENT_SECRET}"
    redirect_uri: "https://gitlab.${DOMAIN}/users/auth/openid_connect/callback"
EOF
}

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="provider=$(providerYaml)" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-gitlab-gitlab-openid.yaml
