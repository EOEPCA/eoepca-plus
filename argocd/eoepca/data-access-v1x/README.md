# Data Access `Application`

The deployment of the Data Access BB relies mostly upon the `data-access` helm chart. There are, however, some additional components to be deployed alongside the core `data-access` chart. Thus, the full Data Access BB deployment comprises...

* Data Access deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* Persistence: PVCs defined for database and for redis
* `Sealed Secret` that provides the credentials for the `CREODIAS EO` data

In order that all 'data-access' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to define the `data-access` deployment using the ArgoCD app-of-apps pattern.

Thus, the root `data-access` application references the `parts/` subdirectory that defines the comprising elements.

```yaml
  source:
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-develop
    path: argocd/eoepca/data-access-v1x/parts
```


## Admin Credentials Sealed Secret

The data-access Creodias EO S3 access credentials are provided via a `Secret` that is maintained securely in git as a `SealedSecret`.

This `SealedSecret` is defined as an element with the `parts/`, and is generated via the script `ss-data-access-auth.sh` via the `sealed-secrets-controller` that is running in the live cluster.

The `<CREODIAS_EODATA_S3_ACCESS_KEY>` and `<CREODIAS_EODATA_S3_ACCESS_SECRET>` are supplied as positional cmdline arguments (with built-in defaults).
