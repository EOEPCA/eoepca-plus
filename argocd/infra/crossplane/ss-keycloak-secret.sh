#!/usr/bin/env bash

set -euo pipefail

ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"

onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT

SOURCE_SECRET_NAME="${SOURCE_SECRET_NAME:-keycloak-provider}"
SOURCE_NAMESPACE="${SOURCE_NAMESPACE:-iam-management}"
SECRET_NAME="${SECRET_NAME:-keycloak-secret}"
NAMESPACE="${NAMESPACE:-workspace}"
OUTPUT_FILE="${OUTPUT_FILE:-parts/ss-${SECRET_NAME}.yaml}"

secretYaml() {
  kubectl -n "${SOURCE_NAMESPACE}" get secret "${SOURCE_SECRET_NAME}" -o json \
    | jq --arg name "${SECRET_NAME}" --arg namespace "${NAMESPACE}" '
        if (.data | type) != "object" then
          error("source Secret has no data")
        else
          {
            apiVersion: "v1",
            kind: "Secret",
            metadata: {
              name: $name,
              namespace: $namespace
            },
            type: (.type // "Opaque"),
            data: .data
          }
        end
      '
}

# Copy the source Secret data without decoding it, retarget it, and seal it for
# the workspace namespace. The plaintext Secret is only passed through pipes.
secretYaml \
  | kubeseal -o yaml --controller-name sealed-secrets --controller-namespace infra \
  | yq '.metadata.annotations."argocd.argoproj.io/sync-wave" = "12"' \
  > "${OUTPUT_FILE}"
