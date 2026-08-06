# Argo Setup

To setup Argo, ensure that you have `kubectl` access to your cluster and run the following command:

```bash
bash scripts/bootstrap-argocd.sh <DOMAIN> <NFS IP> <DNS_API_TOKEN>
```

Wait for a few minutes before you can access the Argo UI at `https://argocd.<DOMAIN>`. The default username is `admin` and the password you can get using:

```bash
echo "Admin password: $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
```
