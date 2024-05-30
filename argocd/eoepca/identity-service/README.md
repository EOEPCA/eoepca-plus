# Identity Service `Application`

The deployment of the Identity Service BB relies mostly upon the `identity-service` helm chart. There are, however, some additional components to be deployed alongside the core `identity-service` chart. Thus, the full Identity Service BB deployment comprises...

* Identity Service deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* Persistence: PVC defined for Keycloak

In order that all Identity Service aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to use an 'ad-hoc' helm chart that provides this wrapper by including (as dependency) the core `identity-service` helm chart, whilst adding the additional parts - ref. [`ad-hoc` helm chart](Chart.yaml).

An [ArgoCD `Application`](app-identity-service.yaml) is then defined that deploys using the 'ad-hoc' wrapper helm chart - thus resulting in a self-contained deployment object for the Identity Service BB in ArgoCD.
