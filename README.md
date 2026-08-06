# eoepca-plus

> **Cluster migration happened 2026-08-06: this branch now deploys to a NEW cluster.**
>
> | | ArgoCD | Rancher | Branch |
> |---|---|---|---|
> | **New cluster (active) RKE2** | https://argocd.develop-v2.eoepca.org/ | https://rancher.develop-v2.eoepca.org/ | `deploy-develop` |
> | Old cluster (frozen, still live) RKE1 | https://argocd.develop.eoepca.org/ | | `deploy-develop-frozen` |
>
> The old cluster at `develop.eoepca.org` has **not** been shut down and is still serving traffic, but it is now pinned to a frozen branch (`deploy-develop-frozen`).
>
> The old cluster will stay live for a **couple of weeks** so anyone can migrate remaining data/config across. Most of the migration has already been done, but some things MAY have been added manually on the old cluster and aren't yet reflected here, this gives you time to declaritvely represent them into this branch/cluster.
>
> IAM resources (clients, users, realms etc) are now declared via **Crossplane**. Do not make manual edits in the Keycloak UI/API, they won't persist and will just drift from what's declared here.
>
> ArgoCD apps are now wired with sync waves, so the new cluster can be torn down and rebuilt fresh regularly.

**All new work should target `deploy-develop`, which now deploys to the new cluster.**

[![Smoke Tests](https://github.com/EOEPCA/eoepca-plus/actions/workflows/run-smoke-tests.yaml/badge.svg)](https://github.com/EOEPCA/eoepca-plus/actions/workflows/run-smoke-tests.yaml)
[![Smoke Tests](https://github.com/EOEPCA/eoepca-plus/actions/workflows/run-acceptance-tests.yaml/badge.svg)](https://github.com/EOEPCA/eoepca-plus/actions/workflows/run-acceptance-tests.yaml)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/EOEPCA/eoepca-plus.svg)](https://github.com/EOEPCA/eoepca-plus/commits)
[![GitHub issues](https://img.shields.io/github/issues/EOEPCA/eoepca-plus.svg)](https://github.com/EOEPCA/eoepca-plus/issues)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

EOEPCA+ deployments for development team

## Virtual Infrastructure

The `deploy` directory contains the Pulumi infrastructure code for setting up the EOEPCA+ platform on OpenStack.
See the corresponding [README](deploy/README.md) for setup instructions.

## ArgoCD Bootstrap

See [README](argocd/README.md) in `argocd` directory.
