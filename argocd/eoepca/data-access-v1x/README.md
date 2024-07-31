# Data Access v1.x `Application`

**_This represents the deployment of the EOEPCA v1.x release line - which is being superceded by the new EOEPCA+ developments._**

The deployment of the Data Access BB relies mostly upon the `data-access` helm chart. There are, however, some additional components to be deployed alongside the core `data-access` chart. Thus, the full Data Access BB deployment comprises...

* Data Access deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* `Sealed Secret` that provides the credentials for the `CREODIAS EO` data

In order that all 'data-access' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to define the `data-access` deployment using the ArgoCD app-of-apps pattern.

Thus, the root `data-access` application references the `parts/` subdirectory that defines the comprising elements.

```yaml
  source:
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-develop
    path: argocd/eoepca/data-access-v1x/parts
```
