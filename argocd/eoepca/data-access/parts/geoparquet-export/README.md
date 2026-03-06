# STAC GeoParquet Export

Automated export of STAC collections from pgstac to GeoParquet format.

## Overview

This solution provides scheduled exports of STAC items to GeoParquet format, supporting both complete and incremental export modes:

- **Complete Export**: Full export of configured collections (monthly by default)
- **Incremental Export**: Sync only changed partitions since last run (daily by default)

## Components

- `exporter.py`: Main export script using stac-geoparquet library
- `Dockerfile`: Container image definition
- `requirements.txt`: Python dependencies

## Configuration

Edit `configmap-geoparquet-config.yaml` to configure collections and partitioning:

```yaml
collections:
  - name: sentinel-2
    partition_by: year  # Options: null, year, month
    start_year: 2015
```

## Schedules

- **Complete**: `0 2 1 * *` (1st of month at 2 AM UTC)
- **Incremental**: `0 3 * * *` (daily at 3 AM UTC)

Modify `schedule` in CronJob manifests to adjust.

## S3 Credentials

The GeoParquet export uses the existing `data-access` secret for CloudFerro S3 credentials (same credentials used by eoAPI services).

No additional secret configuration is needed. The CronJobs are configured to use:
- Bucket: `eoapi-geoparquet`
- Endpoint: `eodata.cloudferro.com`

To use a different bucket, edit the `OUTPUT_PATH` environment variable in the CronJob manifests.

## Build and Deploy

Build the container:

```bash
cd deploy/argocd/eoepca/data-access/parts/geoparquet-export
docker build -t ghcr.io/eoepca/stac-geoparquet-exporter:latest .
docker push ghcr.io/eoepca/stac-geoparquet-exporter:latest
```

ArgoCD will automatically deploy CronJobs when synced.

## Manual Execution

Run export manually:

```bash
kubectl create job --from=cronjob/geoparquet-export-complete manual-export -n data-access
```

## Monitoring

Check job status:

```bash
kubectl get cronjobs -n data-access
kubectl get jobs -n data-access
kubectl logs -n data-access -l app=geoparquet-export
```
