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

SECRET_NAME="ovh-image-repo"
NAMESPACE="iam"

OVH_REPO_USERNAME="${1:-${OVH_REPO_USERNAME:-unknown}}"
OVH_REPO_PASSWORD="${2:-${OVH_REPO_PASSWORD:-changeme}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret docker-registry "${SECRET_NAME}" \
    --docker-server="byud8gih.c1.de1.container-registry.ovh.net" \
    --docker-username="${OVH_REPO_USERNAME}" \
    --docker-password="${OVH_REPO_PASSWORD}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml