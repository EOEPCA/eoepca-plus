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

NAMESPACE="slurm"

# Slurm's shared auth key and the JWT signing key are random bytes, not
# externally issued credentials. They are read from local files (gitignored
# via *.key) so that re-running this script, e.g. through
# argocd/refresh-secrets.sh, reseals the same keys instead of rotating them.
# Both files are generated on first run.
SLURM_KEY_FILE="${SLURM_KEY_FILE:-slurm.key}"
JWT_KEY_FILE="${JWT_KEY_FILE:-jwt_hs256.key}"

for keyFile in "${SLURM_KEY_FILE}" "${JWT_KEY_FILE}"; do
  if [ ! -f "${keyFile}" ]; then
    echo "Generating ${keyFile}"
    dd if=/dev/urandom of="${keyFile}" bs=1024 count=1 2>/dev/null
    chmod 600 "${keyFile}"
  fi
done

# By default kubeseal fetches the controller's public certificate from the
# cluster. To seal without cluster access, export SEALED_SECRETS_CERT=<path>
# to a certificate obtained once with:
#   kubectl -n infra get secret -l sealedsecrets.bitnami.com/sealed-secrets-key \
#     -o jsonpath='{.items[0].data.tls\.crt}' | base64 -d > sealed-secrets.crt
KUBESEAL_ARGS=(-o yaml --controller-name sealed-secrets --controller-namespace infra)
if [ -n "${SEALED_SECRETS_CERT:-}" ]; then
  KUBESEAL_ARGS+=(--cert "${SEALED_SECRETS_CERT}")
fi

# Create Secret and then pipe to kubeseal to create the SealedSecret.
# Written to a temp file first so a failed kubeseal leaves the existing
# SealedSecret untouched.
sealKey() {
  local secretName="$1" secretKey="$2" keyFile="$3"
  local out="parts/ss-${secretName}.yaml"
  if kubectl -n "${NAMESPACE}" create secret generic "${secretName}" \
      --from-file="${secretKey}=${keyFile}" \
      --dry-run=client -o yaml \
      | kubeseal "${KUBESEAL_ARGS[@]}" > "${out}.tmp"; then
    mv "${out}.tmp" "${out}"
  else
    rm -f "${out}.tmp"
    echo "Sealing ${secretName} failed, ${out} left unchanged" >&2
    exit 1
  fi
}

# Names and keys must match slurmKey.secretRef / jwtKey.secretRef in
# parts/values-slurm.yaml
sealKey slurm-auth-key slurm.key "${SLURM_KEY_FILE}"
sealKey slurm-auth-jwt jwt_hs256.key "${JWT_KEY_FILE}"
