# Check if kubeseal is installed
which kubeseal || (curl -sSL https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.3/kubeseal-0.27.3-linux-amd64.tar.gz | tar xz && sudo install kubeseal /usr/local/bin/kubeseal)

# Create and seal the secret
kubectl create secret generic dns-api-token \
    --namespace cert-manager-ns \
    --from-literal=api-token="<YOUR DNS API TOKEN>" \
    --dry-run=client -o yaml | \
    kubeseal --controller-name=sealed-secrets --controller-namespace=infra -o yaml \
    > argocd/infra/cert-manager/parts/ss-dns-api-token.yaml