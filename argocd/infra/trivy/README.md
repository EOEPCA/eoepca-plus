# Trivy `Application`

This scans the cluster for 1) containers with software with known vulnerabilities, and 2) weak Kubernetes configuration.

It deploys the Trivy Operator, which produces CRs (configauditreports and vulnerabilityreports) with scan results, and the ArgoCD Trivy UI extension which displays them.
