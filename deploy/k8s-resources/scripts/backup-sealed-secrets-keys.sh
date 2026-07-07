#!/bin/bash
set -euo pipefail

NAMESPACE="${SEALED_SECRETS_NAMESPACE:-infra}"
BACKUP_FILE="${SEALED_SECRETS_KEY_BACKUP:-resources/sealed-secrets-keys.yaml}"
BACKUP_DIR="$(dirname "${BACKUP_FILE}")"

mkdir -p "${BACKUP_DIR}"
umask 077

until kubectl get secret \
    --namespace "${NAMESPACE}" \
    --selector sealedsecrets.bitnami.com/sealed-secrets-key \
    --no-headers 2>/dev/null | grep -q .; do
    echo "Waiting for the Sealed Secrets controller to create a key..."
    sleep 2
done

TMP_FILE="$(mktemp "${BACKUP_FILE}.tmp.XXXXXX")"
trap 'rm -f "${TMP_FILE}"' EXIT

# Keep only portable fields. Server-managed metadata such as resourceVersion,
# UID and managedFields can prevent the keyring from being created on a clean
# cluster during restore.
kubectl get secret \
    --namespace "${NAMESPACE}" \
    --selector sealedsecrets.bitnami.com/sealed-secrets-key \
    --output json | jq '{
      apiVersion: "v1",
      kind: "List",
      items: [.items[] | {
        apiVersion,
        kind,
        metadata: {
          name: .metadata.name,
          namespace: .metadata.namespace,
          labels: .metadata.labels,
          annotations: .metadata.annotations
        },
        type,
        data
      }]
    }' > "${TMP_FILE}"

chmod 600 "${TMP_FILE}"
mv "${TMP_FILE}" "${BACKUP_FILE}"
trap - EXIT

KEY_COUNT="$(kubectl get secret \
    --namespace "${NAMESPACE}" \
    --selector sealedsecrets.bitnami.com/sealed-secrets-key \
    --no-headers | wc -l)"

echo "Backed up ${KEY_COUNT} Sealed Secrets keys to ${BACKUP_FILE} (mode 600)."
echo "This file contains private keys and is ignored by Git. Copy it to durable, access-controlled secret storage."
