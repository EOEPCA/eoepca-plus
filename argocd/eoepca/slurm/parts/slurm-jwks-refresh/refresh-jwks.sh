#!/bin/sh
# Keeps the ConfigMap with the realm's public signing keys (JWKS) current for
# slurmctld.
#
# 1. Fetch the JWKS from Keycloak and keep only RSA signing keys (RS256).
# 2. If the keys differ from the ConfigMap, write them (server-side apply).
#
# The operator projects the ConfigMap into /etc/slurm of the slurmctld pod.
# With `controller.inplaceReconfigure: true` (values-slurm.yaml), the
# operator's `reconfigure` sidecar notices the changed file and runs
# `scontrol reconfigure`, so slurmctld picks up the new keys without a restart.
set -eu

JWKS_URL="${JWKS_URL:?JWKS_URL is required}"
CONFIGMAP="${JWKS_CONFIGMAP:-slurm-auth-jwks}"
NAMESPACE="${POD_NAMESPACE:?POD_NAMESPACE is required}"

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*"
}

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

curl -fsS --max-time 30 "${JWKS_URL}" -o "${work}/raw.json"

# Keep RSA keys meant for signatures; drop encryption keys. Canonical output,
# so that the comparison below does not depend on key order or whitespace.
python3 -c '
import json, sys
keys = json.load(open(sys.argv[1]))["keys"]
sig = [k for k in keys if k.get("kty") == "RSA" and k.get("use", "sig") == "sig"
       and k.get("alg", "RS256") == "RS256"]
if not sig:
    sys.exit("no RS256 signing key in the JWKS")
sig.sort(key=lambda k: k.get("kid", ""))
print(json.dumps({"keys": sig}, sort_keys=True, separators=(",", ":")))
' "${work}/raw.json" > "${work}/jwks.json"

kubectl get configmap "${CONFIGMAP}" -n "${NAMESPACE}" \
  -o jsonpath='{.data.jwks\.json}' > "${work}/current.json" 2>/dev/null || true

if cmp -s "${work}/jwks.json" "${work}/current.json"; then
  log "JWKS unchanged, nothing to do"
  exit 0
fi

log "JWKS changed, updating ConfigMap ${CONFIGMAP}"
kubectl create configmap "${CONFIGMAP}" -n "${NAMESPACE}" \
    --from-file=jwks.json="${work}/jwks.json" --dry-run=client -o yaml \
  | kubectl apply --server-side --field-manager=slurm-jwks-refresh --force-conflicts -f -
