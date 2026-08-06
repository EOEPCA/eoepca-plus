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

SECRET_NAME="minio-secret"
NAMESPACE="workspace"

# Must match the rootUser/rootPassword used for argocd/infra/minio/parts/ss-minio-auth.yaml,
# since provider-minio authenticates against the same minio instance as that root user.
ACCESS_KEY_ID="${1:-${ROOT_USER:-eoepca}}"
SECRET_ACCESS_KEY="${2:-${ROOT_PASSWORD:-changeme}}"

secretYaml() {
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="AWS_ACCESS_KEY_ID=${ACCESS_KEY_ID}" \
    --from-literal="AWS_SECRET_ACCESS_KEY=${SECRET_ACCESS_KEY}" \
    --dry-run=client -o yaml
}

# Create Secret and then pipe to kubeseal to create the SealedSecret
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra > parts/ss-${SECRET_NAME}.yaml
