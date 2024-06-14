# EOEPCA ArgoCD App-of-apps

## Initial ArgoCD Provisioning (manual)

_Note that this should not be needed, assuming that ArgoCD is installed directly via pulumi._

Create `argocd` namespace...

```bash
kubectl create namespace argocd
```

Install ArgoCD from latest stable release...

```bash
curl -JLs -o argocd.yaml https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml \
  && kubectl apply -n argocd -f argocd.yaml
```

Deploy `Ingress` for ArgoCD...

```bash
kubectl apply -f argocd-ingress.yaml
```

Retrieve intial `admin` password...

```
argocd admin initial-password -n argocd
```

Login as `admin`...

```bash
argocd login argocd.<domain>
  # Username: admin
  # Password: <initial-password>
```

Update `admin` password...

```bash
argocd account update-password  # pattern ^.{8,32}$
```

## Login

Login to argocd...

```bash
argocd login argocd.<domain>
```

Supply credentials of an admin user...

```
  Username: admin
  Password: <admin-password>
```

## Project

Create `eoepca` argocd project...

```bash
argocd proj create eoepca -f https://raw.githubusercontent.com/EOEPCA/eoepca-plus/deploy-rconway/argocd/project.yaml
```

## App-of-apps

The deployment is bootstrapped from the `eoepca` app-of-apps, which is defined as a `Kustomization` in the `argocd/` directory. The `kustomization.yaml` in turn brings in the various components of the full system deployment - each of which is defined as an ArgoCD `Application` - comprising building blocks and infrastructure components on which they depend.

The app--of-apps deployment is triggered using...

```bash
argocd app create eoepca \
  --project eoepca \
  --dest-namespace argocd \
  --dest-server https://kubernetes.default.svc \
  --repo https://github.com/EOEPCA/eoepca-plus \
  --path argocd \
  --revision deploy-rconway \
  --labels 'eoepca/is-root-app="true",eoepca/app-name=eoepca' \
  --sync-policy automated \
  --auto-prune \
  --self-heal \
  --allow-empty
```

Which results in the following `Application` CRD in the `argocd` namespace...

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: eoepca
  namespace: argocd
spec:
  destination:
    namespace: argocd
    server: https://kubernetes.default.svc
  project: eoepca
  source:
    path: argocd
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-rconway
  syncPolicy:
    automated:
      allowEmpty: true
      prune: true
      selfHeal: true
```

## Organisation of Applications

The `Applications` are organised under broad groupings...

* `eoepca`<br>
  _EOEPCA+ building blocks_<br>
  Can be organised into subdirectories, as required, for convenience.<br>
  The deploy of `zoo-dru` as an ArgoCD `Application` provides an example of a helm chart deployment with the values being provided through multiple dedicated values files. See the [Zoo-DRU deployment README](eoepca/zoo-dru/README.md).
* `infra`<br>
  Services that support the building blocks, including...
  * Sealed Secrets<br>
    _Secure management of k8s secrets in git_
  * Minio<br>
    _S3-compatible Object Storage_<br>
    See [minio deployment README](infra/minio/README.md) for details of the deployment of this composite `Application`. This provides an example of an approach to wrap a more complex service deployment into a self-contained ArgoCD `Application`.
  * Harbor<br>
    _Container registry_
* `test`<br>
  _Resources used for testing/debugging - such as the `dummy` service_

