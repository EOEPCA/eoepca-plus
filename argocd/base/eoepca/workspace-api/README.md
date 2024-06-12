# Workspace API `Application`

The deployment of the Workspace API relies mostly upon the `rm-workspace-api` helm chart. There are, however, some additional components to be deployed alongside the core `rm-workspace-api` chart. Thus, the full Workspace API deployment comprises...

* Workspace API deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* 'Workspace Templates' (aka `workspace-charts`) defined as a `ConfigMap`
* `HelmRepository` resource used by `flux` during workspace creation
* `SealedSecret` for access to Harbor container registry

In order that all Workspace API aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to use an 'ad-hoc' helm chart that provides this wrapper by including (as dependency) the core `rm-workspace-api` helm chart, whilst adding the additional parts - ref. [`ad-hoc` helm chart](Chart.yaml).

An [ArgoCD `Application`](app-workspace-api.yaml) is then defined that deploys using the 'ad-hoc' wrapper helm chart - thus resulting in a self-contained deployment object for the Workspace API in ArgoCD.
