# Workspace API `Application`

The deployment of the Workspace API relies mostly upon the `rm-workspace-api` helm chart. There are, however, some additional components to be deployed alongside the core `rm-workspace-api` chart. Thus, the full Workspace API deployment comprises...

* Workspace API deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* 'Workspace Templates' (aka `workspace-charts`) defined as a `ConfigMap`
* `HelmRepository` resource used by `flux` during workspace creation
* `SealedSecret` for access to Harbor container registry

In order that all 'rm-workspace-api' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to define the `rm-workspace-api` deployment using the ArgoCD app-of-apps pattern.

Thus, the root `rm-workspace-api` application references the `parts/` subdirectory that defines the comprising elements.

```yaml
  source:
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-develop
    path: argocd/eoepca/rm-workspace-api/parts
```
