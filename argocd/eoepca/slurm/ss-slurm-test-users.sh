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

SECRET_NAME="slurm-test-users"
NAMESPACE="iam-management"

# Passwords of the Keycloak test users in parts/iam.yaml. Missing values are
# generated and appended to the local, gitignored .env, so that the person who
# sealed them can log in and re-running the script reseals the same values.
for var in SLURM_TEST_1_PASSWORD SLURM_TEST_2_PASSWORD; do
  if [ -z "${!var:-}" ]; then
    value="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)"
    printf -v "${var}" '%s' "${value}"
    echo "${var}=${value}" >> .env
    chmod 600 .env
    echo "Generated ${var} (stored in $(pwd)/.env)"
  fi
done

# See ss-slurm-auth.sh for sealing without cluster access (SEALED_SECRETS_CERT).
KUBESEAL_ARGS=(-o yaml --controller-name sealed-secrets --controller-namespace infra)
if [ -n "${SEALED_SECRETS_CERT:-}" ]; then
  KUBESEAL_ARGS+=(--cert "${SEALED_SECRETS_CERT}")
fi

out="parts/ss-${SECRET_NAME}.yaml"
if kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal="slurm-test-1-password=${SLURM_TEST_1_PASSWORD}" \
    --from-literal="slurm-test-2-password=${SLURM_TEST_2_PASSWORD}" \
    --dry-run=client -o yaml \
    | kubeseal "${KUBESEAL_ARGS[@]}" > "${out}.tmp"; then
  mv "${out}.tmp" "${out}"
else
  rm -f "${out}.tmp"
  echo "Sealing ${SECRET_NAME} failed, ${out} left unchanged" >&2
  exit 1
fi
