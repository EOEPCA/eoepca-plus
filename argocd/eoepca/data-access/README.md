# Data Access `Application`

The deployment of the Data Access BB relies mostly upon the `data-access` helm chart. There are, however, some additional components to be deployed alongside the core `data-access` chart. Thus, the full Data Access BB deployment comprises...

* Data Access deployed via helm chart - defined in [EOEPCA Helm Chart Repo](https://eoepca.github.io/helm-charts)
* Persistence: PVCs defined for database and for redis

In order that all 'data-access' aspects are deployed under the umbrella of a single ArgoCD `Application`, the approach is to use an 'ad-hoc' helm chart that provides this wrapper by including (as dependency) the core `data-access` helm chart, whilst adding the additional parts - ref. [`ad-hoc` helm chart](Chart.yaml).

An [ArgoCD `Application`](app-data-access.yaml) is then defined that deploys using the 'ad-hoc' wrapper helm chart - thus resulting in a self-contained deployment object for the Data Access BB in ArgoCD.
