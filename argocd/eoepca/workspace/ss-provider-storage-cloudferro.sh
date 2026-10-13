#!/usr/bin/env bash
# Discover the CloudFerro workspace projects and generate the SealedSecrets
# used by the Storage Composition. This script does not change OpenStack or
# apply resources to Kubernetes.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(mktemp -d /tmp/xyz-cloudferro-secrets.XXXXXX)"

EXPECTED_SECRET_COUNT=2
KUBERNETES_NAMESPACE=workspace
SEALED_SECRETS_CONTROLLER_NAME=sealed-secrets
SEALED_SECRETS_CONTROLLER_NAMESPACE=infra
PROVIDER_STORAGE_COMMIT=39c39bb5654b7cb2658eb234486b1312982fa29c
PROVIDER_STORAGE_SOURCE="https://raw.githubusercontent.com/versioneer-tech/provider-storage/${PROVIDER_STORAGE_COMMIT}/cloudferro/dependencies"
OUTPUT_FILE="${SCRIPT_DIR}/parts/ss-provider-storage-cloudferro.yaml"

cleanup() {
  exit_status=$?
  rm -rf -- "$WORK_DIR"
  if ((exit_status != 0)); then
    printf 'FAILED\n' >&2
  fi
}
trap cleanup EXIT

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

(($# == 0)) || die 'This script does not accept arguments.'

required_commands=(curl jq kubeseal openstack sed sort tee wc yq)
for required_command in "${required_commands[@]}"; do
  command -v "$required_command" >/dev/null 2>&1 ||
    die "Required command not found: $required_command"
done

[[ ${HOME:-} = /* ]] || die 'HOME must be an absolute path.'
KUBECONFIG_FILE="$HOME/.kube/config-eoepca-demo"
credentials_file=${CROSSPLANE_CLOUDFERRO_CREDENTIALS_FILE:-}
if [[ -z $credentials_file ]]; then
  credentials_file="$HOME/.config/provider-storage/cloudferro-creds.json"
fi
export CROSSPLANE_CLOUDFERRO_CREDENTIALS_FILE=$credentials_file

export CROSSPLANE_CLOUDFERRO_NAMESPACE=$KUBERNETES_NAMESPACE
export CROSSPLANE_CLOUDFERRO_PROJECT_PATTERN=${CROSSPLANE_CLOUDFERRO_PROJECT_PATTERN:-'^eoepca-ws-[0-9]{4}$'}
export CROSSPLANE_CLOUDFERRO_ADMIN_CLOUD=${CROSSPLANE_CLOUDFERRO_ADMIN_CLOUD:-current}
export CROSSPLANE_CLOUDFERRO_DOMAIN_ID=${CROSSPLANE_CLOUDFERRO_DOMAIN_ID:-$(jq -er '.identity.domain_id' "$credentials_file")}
export CROSSPLANE_CLOUDFERRO_AUTH_URL=${CROSSPLANE_CLOUDFERRO_AUTH_URL:-$(jq -er '.identity.auth_url' "$credentials_file")}
export CROSSPLANE_CLOUDFERRO_REGION=${CROSSPLANE_CLOUDFERRO_REGION:-$(jq -er '.identity.region' "$credentials_file")}

printf 'Discovering matching CloudFerro projects.\n' >&2
iam_dir="$WORK_DIR/provider-storage/cloudferro/dependencies"
mkdir -p "$iam_dir"
for source_file in iam.sh password_prompt.py; do
  curl --fail --silent --show-error --location \
    "$PROVIDER_STORAGE_SOURCE/$source_file" --output "$iam_dir/$source_file"
done
chmod +x "$iam_dir/iam.sh"
"$iam_dir/iam.sh" status |
  tee "$WORK_DIR/cloudferro-status.txt"
sed -nE \
  's/^project=([0-9a-f]{32}) project_name=.* controller_user_id=.*$/\1/p' \
  "$WORK_DIR/cloudferro-status.txt" |
  LC_ALL=C sort -u >"$WORK_DIR/project-ids"
project_count=$(wc -l <"$WORK_DIR/project-ids")
[[ $project_count -eq $EXPECTED_SECRET_COUNT ]] ||
  die "Expected ${EXPECTED_SECRET_COUNT} matching CloudFerro projects, but found ${project_count}."

projects=$(jq -Rn '[inputs]' <"$WORK_DIR/project-ids")
jq --argjson projects "$projects" '.projects = $projects' \
  "$credentials_file" >"$WORK_DIR/discovered-credentials.json"
chmod 600 "$WORK_DIR/discovered-credentials.json"
export CROSSPLANE_CLOUDFERRO_CREDENTIALS_FILE="$WORK_DIR/discovered-credentials.json"
"$iam_dir/iam.sh" render-secrets \
  >"$WORK_DIR/plain-secrets.yaml"
yq ea -N -o=json -I=0 \
  'select(.apiVersion == "v1" and .kind == "Secret")' \
  "$WORK_DIR/plain-secrets.yaml" |
  jq -sc 'sort_by(.metadata.name)[]' >"$WORK_DIR/plain-secrets.jsonl"

secret_count=$(wc -l <"$WORK_DIR/plain-secrets.jsonl")
[[ $secret_count -eq $EXPECTED_SECRET_COUNT ]] ||
  die "Expected ${EXPECTED_SECRET_COUNT} rendered Secrets, but found ${secret_count}."

kubeseal \
  --kubeconfig="$KUBECONFIG_FILE" \
  --controller-name="$SEALED_SECRETS_CONTROLLER_NAME" \
  --controller-namespace="$SEALED_SECRETS_CONTROLLER_NAMESPACE" \
  --fetch-cert >"$WORK_DIR/sealed-secrets.pem"

: >"$WORK_DIR/ss-provider-storage-cloudferro.yaml"
sealed_count=0
while IFS= read -r secret_json; do
  secret_name=$(jq -er '.metadata.name' <<<"$secret_json")
  printf '%s\n' "$secret_json" >"$WORK_DIR/plain-secret.json"
  kubeseal \
    --cert="$WORK_DIR/sealed-secrets.pem" \
    --format=yaml \
    --secret-file="$WORK_DIR/plain-secret.json" \
    >"$WORK_DIR/sealed-secret.yaml"
  SECRET_NAME=$secret_name KUBERNETES_NAMESPACE=$KUBERNETES_NAMESPACE yq -e '
    .kind == "SealedSecret" and
    .metadata.name == strenv(SECRET_NAME) and
    .metadata.namespace == strenv(KUBERNETES_NAMESPACE) and
    (.spec.encryptedData.config | type == "!!str" and length > 0)
  ' "$WORK_DIR/sealed-secret.yaml" >/dev/null ||
    die "kubeseal produced an invalid SealedSecret for $secret_name."
  printf '%s\n' '---' >>"$WORK_DIR/ss-provider-storage-cloudferro.yaml"
  yq 'del(.metadata.creationTimestamp, .spec.template.metadata.creationTimestamp) |
      ... comments = ""' "$WORK_DIR/sealed-secret.yaml" \
    >>"$WORK_DIR/ss-provider-storage-cloudferro.yaml"
  ((sealed_count += 1))
done <"$WORK_DIR/plain-secrets.jsonl"

[[ $sealed_count -eq $EXPECTED_SECRET_COUNT ]] ||
  die "Expected ${EXPECTED_SECRET_COUNT} SealedSecrets, but created ${sealed_count}."

mv -- "$WORK_DIR/ss-provider-storage-cloudferro.yaml" "$OUTPUT_FILE"
chmod 644 "$OUTPUT_FILE"

printf 'Created %s with %s CloudFerro project SealedSecrets.\n' \
  "$OUTPUT_FILE" "$sealed_count" >&2
