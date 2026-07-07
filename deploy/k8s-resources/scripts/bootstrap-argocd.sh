#!/bin/bash
set -e

# Check kubectl is working
if ! kubectl get nodes &>/dev/null; then
    echo "ERROR: kubectl cannot reach the cluster. Check your KUBECONFIG."
    exit 1
fi

DOMAIN="${1:?Usage: $0 <domain> <nfs-ip> <dns-api-token> [argocd-version]}"
NFS_IP="${2:?Usage: $0 <domain> <nfs-ip> <dns-api-token> [argocd-version]}"
DNS_API_TOKEN="${3:?Usage: $0 <domain> <nfs-ip> <dns-api-token> [argocd-version]}"
ARGOCD_VERSION="${4:-9.5.12}"
NFS_PROVISIONER_VERSION="4.0.12"
SEALED_SECRETS_KEY_BACKUP="${SEALED_SECRETS_KEY_BACKUP:-resources/sealed-secrets-keys.yaml}"

ARGOCD_DOMAIN="argocd.${DOMAIN}"

echo "=== applying sealed secrets keys ==="
kubectl create namespace infra 2>/dev/null || true
if [[ -s "${SEALED_SECRETS_KEY_BACKUP}" ]]; then
    kubectl apply -f "${SEALED_SECRETS_KEY_BACKUP}"
else
    echo "ERROR: No Sealed Secrets key backup found at ${SEALED_SECRETS_KEY_BACKUP}."
    echo "Restore the original keyring before starting the controller; repository SealedSecrets depend on it."
    exit 1
fi

echo "=== installing sealed secrets controller ==="
helm upgrade --install sealed-secrets \
    https://github.com/bitnami-labs/sealed-secrets/releases/download/helm-v2.16.0/sealed-secrets-2.16.0.tgz \
    --namespace infra \
    --create-namespace \
    --wait --timeout 3m

# The controller generates a new sealing key when it starts. Back up the full
# keyring immediately: old SealedSecrets still require their original keys.
SEALED_SECRETS_KEY_BACKUP="${SEALED_SECRETS_KEY_BACKUP}" \
    scripts/backup-sealed-secrets-keys.sh


echo "=== Installing cert-manager ==="
helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --set crds.enabled=true \
    --set clusterResourceNamespace=cert-manager-ns \
    --wait --timeout 3m


echo "=== applying dns-api-token secret ==="
kubectl create namespace cert-manager-ns 2>/dev/null || true
kubectl create secret generic dns-api-token \
    --namespace cert-manager-ns \
    --from-literal=api-token="${DNS_API_TOKEN}" \
    --dry-run=client -o yaml | \
    kubectl annotate --local -f - \
        sealedsecrets.bitnami.com/managed=true \
        -o yaml | kubectl apply -f -


# Also store as a sealed secret for ArgoCD to use in the Git repository
kubectl create secret generic dns-api-token \
    --namespace cert-manager-ns \
    --from-literal=api-token="${DNS_API_TOKEN}" \
    --dry-run=client -o yaml | \
    kubeseal --controller-name=sealed-secrets --controller-namespace=infra -o yaml \
    > ../../argocd/infra/cert-manager/parts/ss-dns-api-token.yaml

kubectl apply -f ../../argocd/infra/cert-manager/parts/ss-dns-api-token.yaml


echo "=== Installing cluster issuer ==="
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@${DOMAIN}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF


echo "=== Installing NFS Provisioner ==="
helm repo add nfs-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
# helm repo update

helm upgrade --install nfs-provisioner nfs-provisioner/nfs-subdir-external-provisioner \
    --set nfs.server="${NFS_IP}" \
    --set nfs.path=/data/dynamic \
    --set storageClass.name=managed-nfs-storage \
    --set storageClass.reclaimPolicy=Delete \
    --set storageClass.allowVolumeExpansion=true \
    --version "${NFS_PROVISIONER_VERSION}" \
    --wait --timeout 3m

helm upgrade --install nfs-provisioner-retain nfs-provisioner/nfs-subdir-external-provisioner \
    --set nfs.server="${NFS_IP}" \
    --set nfs.path=/data/dynamic \
    --set storageClass.name=managed-nfs-storage-retain \
    --set storageClass.reclaimPolicy=Retain \
    --set storageClass.allowVolumeExpansion=true \
    --set provisionerName=nfs-storage-retain \
    --version "${NFS_PROVISIONER_VERSION}" \
    --wait --timeout 3m

echo "=== Installing ArgoCD ==="
helm repo add argo https://argoproj.github.io/argo-helm
# helm repo update

kubectl create namespace argocd 2>/dev/null || true

helm upgrade --install argocd argo/argo-cd \
    --namespace argocd \
    --version "${ARGOCD_VERSION}" \
    -f argocd/argocd-values.yaml \
    --set crds.install=true \
    --set crds.keep=true \
    --set server.service.type=ClusterIP \
    --set "server.extraArgs[0]=--insecure" \
    --set server.ingress.enabled=true \
    --set server.ingress.hostname="${ARGOCD_DOMAIN}" \
    --set "server.ingress.annotations.kubernetes\.io/ingress\.class=nginx" \
    --set "server.ingress.annotations.cert-manager\.io/cluster-issuer=letsencrypt-prod" \
    --set "server.ingress.hosts[0]=${ARGOCD_DOMAIN}" \
    --set "server.ingress.tls[0].hosts[0]=${ARGOCD_DOMAIN}" \
    --set "server.ingress.tls[0].secretName=argocd-server-tls" \
    --set applicationSet.enabled=true \
    --set dex.enabled=true \
    --set configs.cm.url="https://${ARGOCD_DOMAIN}" \
    --set configs.cm.application\.resourceTrackingMethod=annotation+label \
    --wait --timeout 5m

echo "=== Waiting for ArgoCD CRDs ==="
until kubectl get crd applications.argoproj.io &>/dev/null; do
    sleep 5
done
until kubectl get crd appprojects.argoproj.io &>/dev/null; do
    sleep 5
done

kubectl create namespace ingress-nginx-ns --dry-run=client -o yaml | kubectl apply -f -

echo "=== Creating ArgoCD Project and Application ==="
kubectl apply -f argocd/project.yaml
kubectl apply -f argocd/application.yaml

echo ""
echo "=== Done ==="
echo ""
echo "ArgoCD UI: https://${ARGOCD_DOMAIN}"
echo "Admin username: admin"
echo "Admin password: $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
echo ""
echo "Rancher UI: https://rancher.${DOMAIN}"
echo "Rancher Password: $(kubectl -n cattle-system get secret bootstrap-secret -o jsonpath='{.data.bootstrapPassword}' | base64 -d)"
echo ""
