# Identity Service `Application`

The deployment of the Identity Service BB relies mostly upon the `identity-service` helm chart. There are, however, some additional components to be deployed alongside the core `identity-service` chart. Thus, the full Identity Service BB deployment comprises...

* Identity Service deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* Persistence: PVC defined for Keycloak

In order that all 'identity-service' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to define the `identity-service` deployment using the ArgoCD app-of-apps pattern.

Thus, the root `identity-service` application references the `parts/` subdirectory that defines the comprising elements.

```yaml
  source:
    repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-develop
    path: argocd/eoepca/identity-service/parts
```
