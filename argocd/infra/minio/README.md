# Minio `Application`

The deployment of `minio` relies mostly upon the minio helm chart. There are, however, some additional components to be deployed alongside the core minio chart. Thus, the full minio deployment comprises...

* Minio deployed via upstream helm chart
* Minio Bucket API deployed via its dedicated helm chart
* `Sealed Secret` that provides the credentials for the `admin` user

In order that all 'minio' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to use an 'ad-hoc' helm chart that provides this wrapper by including (as dependency) the core minio helm chart, whilst adding the additional parts - ref. [`ad-hoc` helm chart](Chart.yaml).

An ArgoCD `Application` is then defined that deploys using the 'ad-hoc' wrapper helm chart - thus resulting in a self-contained deployment object for minio in ArgoCD.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: minio
  namespace: argocd
spec:
  # Ref. https://argo-cd.readthedocs.io/en/stable/user-guide/application-specification/
  project: eoepca
  source:
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-develop
    path: argocd/infra/minio

    helm:
      releaseName: minio
      valuesObject:
        minio:
          # minio helm values...
```

## Admin Credentials Sealed Secret

The minio admin credentials are provided via a `Secret` that is maintained securely in git as a `SealedSecret`. This is deined as a template in the ad-hoc helm chart - ref. [ss-minio-auth.yaml](templates/ss-minio-auth.yaml).

The `encryptedData` for the `minio-auth` SealedSecret is provided through helm values that are configured in the file `admin-credentials.yaml` that is presented via the ArgoCD `Application` through the `valueFiles` directive.

The script `ss-minio-auth.sh` is used the generate this encrypted data via the `sealed-secrets-controller` that is running in the live cluster.<br>
The `<rootUser>` and `<rootPassword>` are supplied as positional cmdline arguments (with built-in defaults).
