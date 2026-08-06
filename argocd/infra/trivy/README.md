# Trivy `Application`

This scans the cluster for 1) containers with software with known vulnerabilities, and 2) weak Kubernetes configuration.

It deploys the Trivy Operator, which produces CRs (configauditreports and vulnerabilityreports) with scan results.

The ArgoCD Trivy UI extension that displays these reports in the ArgoCD UI is *not* deployed by this `Application`. It patches the `argocd-server` Pod spec via an init container, so it's configured as part of ArgoCD's own Helm release instead: see `server.extensions` in `deploy/k8s-resources/argocd/argocd-values.yaml`.
