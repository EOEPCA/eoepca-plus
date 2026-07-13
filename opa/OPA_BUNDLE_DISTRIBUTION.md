# OPA Bundle Distribution with GitHub Container Registry via ORAS

This setup builds the OPA bundle directly from this repository under `opa/bundle` and publishes it to GitHub Container Registry using ORAS (OCI Registry As Storage).

## Repository Layout

```
eoepca-plus/
├── opa/
│   ├── bundle/
│   │   ├── data.yaml
│   │   └── policy/
│   ├── config.json
│   └── OPA_BUNDLE_DISTRIBUTION.md
├── .github/workflows/build-opa-bundle.yaml
└── argocd/eoepca/data-proxy/parts/opa-config.yaml
```

## CI Workflow

The workflow in `.github/workflows/build-opa-bundle.yaml` builds the OPA bundle and pushes it to GitHub Container Registry using ORAS.

Triggers:
- push on `main`, `develop`, and `deploy-develop` when `opa/**` changes
- pull request to `main` when `opa/**` changes (build only)
- manual dispatch

## OPA Runtime Configuration

`argocd/eoepca/data-proxy/parts/opa-config.yaml` should point to GHCR with the ORAS-compatible OCI image.

## Local Validation & Push

### Build the bundle locally

```bash
cd eoepca-plus
opa build -b ./opa/bundle -o ./bundle.tar.gz
tar -tzf ./bundle.tar.gz | head -20
```

### Push with ORAS

Install ORAS if not already available:
```bash
# Install ORAS (see https://oras.land/)
curl -sSLO https://github.com/oras-project/oras/releases/download/v1.1.0/oras_1.1.0_linux_amd64.tar.gz
tar xzf oras_1.1.0_linux_amd64.tar.gz
export PATH="$(pwd):$PATH"
```

Create a `config.json` for the OPA bundle:
```json
{
  "mediaType": "application/vnd.oci.image.config.v1+json",
  "version": "1.0.0",
  "created": "2024-01-01T00:00:00Z",
  "description": "OPA Policy Bundle",
  "org.opencontainers.image.source": "https://github.com/EOEPCA/eoepca-plus"
}
```

Push to GHCR:
```bash
export REGISTRY=ghcr.io
export ORG=eoepca
export BUNDLE_VERSION=1.0.0  # Update as needed

# Log in to GHCR (requires GITHUB_TOKEN with packages:write)
echo $GITHUB_TOKEN | oras login $REGISTRY -u <username> --password-stdin

# Push the bundle
oras push $REGISTRY/$ORG/opa-bundle:$BUNDLE_VERSION \
  --config config.json:application/vnd.oci.image.config.v1+json \
  bundle.tar.gz:application/vnd.oci.image.layer.v1.tar+gzip
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

3. Bundle push issues
   - Verify ORAS is installed: `oras version`
   - Ensure GITHUB_TOKEN has `write:packages` and `read:packages` scopes
   - Check login: `oras login ghcr.io -u <username>`
   - Verify bundle exists: `ls -lh bundle.tar.gz`

4. Bundle fetch issues with OPA
   - OPA supports `oras://` scheme for bundle references
   - Example: `oras://ghcr.io/eoepca/opa-bundle:1.0.0`
   - Verify in OPA logs for bundle download errors

### Bundle Signing (Optional)

For production environments, consider:
- OPA bundle signing and verification
- Image signing with Cosign
- Policy as code for bundle contents

## Related Documentation

- [OPA Bundle Documentation](https://www.openpolicyagent.org/docs/latest/management-bundles/)
- [ORAS Documentation](https://oras.land/)
- [OCI Image Spec](https://github.com/opencontainers/image-spec)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Kubernetes Secret Management](https://kubernetes.io/docs/concepts/configuration/secret/)
