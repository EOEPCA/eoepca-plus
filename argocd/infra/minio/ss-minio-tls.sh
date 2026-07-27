#!/usr/bin/env bash
set -euo pipefail

# Backs up the currently-issued minio-tls Secret (a real cert-manager
# certificate, already validated by Let's Encrypt) as a SealedSecret, so a
# clean/reset cluster restores the same valid cert instead of requesting a
# fresh one from the ACME server on every RKE2 reset. cert-manager treats an
# existing, unexpired Secret that matches the Certificate spec as Ready and
# skips issuance entirely, regardless of which issuer originally signed it.
#
# Run this once, any time after minio-tls shows Ready=True:
#   kubectl -n infra get certificate minio-tls
#
# Re-run it after each renewal (~every 60 days) to keep the backup current;
# an out-of-date backup just restores an older (but still valid, until
# expiry) cert -- it doesn't break anything.

ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"

onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT

SECRET_NAME="minio-tls"
NAMESPACE="infra"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"; onExit' EXIT

kubectl -n "${NAMESPACE}" get secret "${SECRET_NAME}" -o jsonpath='{.data.tls\.crt}' \
  | base64 -d > "${TMP_DIR}/tls.crt"
kubectl -n "${NAMESPACE}" get secret "${SECRET_NAME}" -o jsonpath='{.data.tls\.key}' \
  | base64 -d > "${TMP_DIR}/tls.key"

kubectl -n "${NAMESPACE}" create secret tls "${SECRET_NAME}" \
    --cert="${TMP_DIR}/tls.crt" --key="${TMP_DIR}/tls.key" \
    --dry-run=client -o yaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra \
  > parts/ss-${SECRET_NAME}.yaml

echo "Wrote parts/ss-${SECRET_NAME}.yaml"
echo "Next: add it to parts/kustomization.yaml's resources list (see ss-minio-auth.yaml for the existing pattern)."
