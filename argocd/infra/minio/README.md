# Minio `Application`

The deployment of `minio` relies mostly upon the minio helm chart. There are, however, some additional components to be deployed alongside the core minio chart. Thus, the full minio deployment comprises...

* Minio deployed via upstream helm chart
* Minio Bucket API deployed via its dedicated helm chart
* `Sealed Secret` that provides the credentials for the `admin` user

In order that all 'minio' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to define the `minio` deployment using the ArgoCD app-of-apps pattern.

Thus, the root `minio` application references the `parts/` subdirectory that defines the comprising elements.

```yaml
  source:
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-develop
    path: argocd/infra/minio/parts
```

## Admin Credentials Sealed Secret

The minio admin credentials are provided via a `Secret` that is maintained securely in git as a `SealedSecret`.

This `SealedSecret` is defined as an element with the `parts/`, and is generated via the script `ss-minio-auth.sh` via the `sealed-secrets-controller` that is running in the live cluster.

The `<rootUser>` and `<rootPassword>` are supplied as positional cmdline arguments (with built-in defaults).
