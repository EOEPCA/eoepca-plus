# Zoo-DRU with the Slurm runner

ZOO-Project DRU (OGC API - Processes) that runs CWL Application Packages as Slurm jobs on the
cluster in `argocd/eoepca/slurm`, through the Slurm REST API, under the POSIX account of the
requesting user.

Deployed like `zoo-dru-std`: an ArgoCD `Application` with the `zoo-project-dru` helm chart and
values from `parts/values-zoo.yaml`. Differences:

* **Image** `ghcr.io/eoepca/eoepca-plus/zoo-project-slurm` (`images/zoo-project-slurm`): the ZOO
  image plus the Python package `zoo_slurm_runner`. The service template
  (`cookiecutter.templateUrl`) selects this runner.
* **Identity.** The gateway checks the user's token and the per-user path. The runner exchanges
  the token (Keycloak Standard Token Exchange) for a token of `zoo-slurm-runner`, which carries
  the claim `sun` from the admin-only user attribute `slurm_user`. Slurm runs the job under that
  account. A user without `slurm_user` cannot submit. See the comments in `parts/iam.yaml`.
* **Job states** are read with a token of `zoo-slurm-poller` (account `zoo-poll`), so that jobs
  can run longer than the user's token.
* **No open route.** ZOO does not check that the user in the path is the user in the token; the
  `authz-keycloak` plugin does (`parts/ingress-zoo.yaml`).
* **Least privilege.** `clusterAdminRoleName: view`: the Slurm runner creates no Kubernetes
  objects.

## Use

Get a token for a Slurm test user (password grant of the client `zoo-slurm`), then use the
user's path, for example:

```
POST https://zooslurm.develop-v2.eoepca.org/slurm-test-1/ogc-api/processes                  (deploy, application/cwl+yaml)
POST https://zooslurm.develop-v2.eoepca.org/slurm-test-1/ogc-api/processes/{id}/execution   (Prefer: respond-async)
GET  https://zooslurm.develop-v2.eoepca.org/slurm-test-1/ogc-api/jobs/{jobId}
GET  https://zooslurm.develop-v2.eoepca.org/slurm-test-1/ogc-api/jobs/{jobId}/results
```

A new user needs: the Keycloak attribute `slurm_user`, an entry in
`slurm/parts/configmap-slurm-nss.yaml`, and a UMA resource, policy and permission in
`parts/iam.yaml`.

## Known limits

* **Dismiss** (`DELETE /jobs/{id}`) removes the ZOO job but does not cancel the Slurm job: the
  chart's `runDismiss` only knows the WES and Calrissian runners, and the chart offers no value to
  replace it.
* **Restart of ZOO-FPM during a job**: ZOO does not resume the job. The Slurm job finishes and
  stages out, but the OGC job stays `running`.
