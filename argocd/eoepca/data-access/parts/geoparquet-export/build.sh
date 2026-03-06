#!/bin/bash
set -e

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/eoepca/stac-geoparquet-exporter}"
TAG="${TAG:-latest}"

echo "Building ${IMAGE_NAME}:${TAG}"

cd "$(dirname "$0")"

docker build -t "${IMAGE_NAME}:${TAG}" .

echo "Build complete. Push with:"
echo "  docker push ${IMAGE_NAME}:${TAG}"