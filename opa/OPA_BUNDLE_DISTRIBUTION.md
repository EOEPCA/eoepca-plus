# OPA Bundle Distribution with GitHub Container Registry

This setup builds the OPA bundle directly from this repository under `opa/bundle` and publishes it to GitHub Container Registry.

## Repository Layout

```
eoepca-plus/
├── opa/
│   ├── bundle/
│   │   ├── data.yaml
│   │   └── policy/
│   ├── Dockerfile.bundle
│   └── OPA_BUNDLE_DISTRIBUTION.md
├── .github/workflows/build-opa-bundle.yaml
└── argocd/eoepca/data-proxy/parts/opa-config.yaml
```

## CI Workflow

The workflow in `.github/workflows/build-opa-bundle.yaml` builds and pushes OCI image to `ghcr.io/<org>/opa-bundle`.

Triggers:
- push on `main` and `develop` when `opa/**` changes
- pull request to `main` when `opa/**` changes (build only)
- manual dispatch

## OPA Runtime Configuration

`argocd/eoepca/data-proxy/parts/opa-config.yaml` should point to GHCR:

## Local Validation

```bash
cd eoepca-plus
opa build -b ./opa/bundle -o ./bundle.tar.gz
tar -tzf ./bundle.tar.gz | head -20
```

## Kubernetes Secret

```bash
kubectl create secret generic opa-credentials \
  --from-literal=GITHUB_TOKEN=$GITHUB_TOKEN \
  -n data-proxy
```

## Troubleshooting

1. Build fails in CI
   - Verify `opa/bundle` exists and contains valid Rego/YAML.
   - Run `opa build -b ./opa/bundle` locally.

2. OPA does not refresh bundle
   - Check sidecar logs: `kubectl logs -n data-proxy <pod> -c opa | grep -i bundle`.
   - Verify `GITHUB_TOKEN` is present in namespace `data-proxy`.

3. Image pull issues
   - Confirm image exists: `docker pull ghcr.io/eoepca/opa-bundle:latest`.
   - Confirm token has package read access.
      max_delay_seconds: 0
```

### Bundle Signing (Optional)

For production environments, consider:
- OPA bundle signing and verification
- Image signing with Cosign
- Policy as code for bundle contents

## Related Documentation

- [OPA Bundle Documentation](https://www.openpolicyagent.org/docs/latest/management-bundles/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Kubernetes Secret Management](https://kubernetes.io/docs/concepts/configuration/secret/)
