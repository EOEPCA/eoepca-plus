# slurmd with a CWL engine and a container runtime, for CWL Application
# Packages submitted through the Slurm REST API.
#
# Base: the Slinky slurmd image, same build as the rest of the Slurm cluster
# (argocd/eoepca/slurm/parts/values-slurm.yaml). Ubuntu 26.04.
# Added:
#   - Apptainer from the Ubuntu archive (unprivileged, user namespaces;
#     the upstream .deb files target older Ubuntu releases)
#   - cwltool in /opt/cwl, on PATH as `cwltool`; the resolved Python
#     packages are recorded in /opt/cwl/requirements.lock
#   - nodejs for CWL JavaScript expressions
#
# Jobs run `cwltool --singularity`, which runs the Docker images of an
# Application Package through Apptainer. The slurmd container itself is
# privileged in Slinky; Apptainer needs no further pod rights.
ARG SLURMD_IMAGE=ghcr.io/slinkyproject/slurmd:26.05.4-ubuntu26.04
FROM ${SLURMD_IMAGE}

ARG CWLTOOL_VERSION=3.3.20260925135507

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates python3-venv nodejs apptainer; \
    python3 -m venv /opt/cwl; \
    /opt/cwl/bin/pip install --no-cache-dir "cwltool==${CWLTOOL_VERSION}"; \
    ln -s /opt/cwl/bin/cwltool /usr/local/bin/cwltool; \
    /opt/cwl/bin/pip freeze > /opt/cwl/requirements.lock; \
    rm -rf /var/lib/apt/lists/*; \
    apptainer --version; \
    cwltool --version

LABEL org.opencontainers.image.title="slurmd-cwl" \
      org.opencontainers.image.description="Slinky slurmd with Apptainer and cwltool" \
      org.opencontainers.image.source="https://github.com/EOEPCA/eoepca-plus"
