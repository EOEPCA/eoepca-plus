# ZOO-Project DRU with the Slurm runner (zoo-slurm-runner), for argocd/eoepca/zoo-dru-slurm.
#
# Base: the ZOO-Project DRU image that the zoo-project-dru chart 0.10.4 uses by default.
# Added: the Python package zoo_slurm_runner. It submits the wrapped CWL Application
# Package as one Slurm job through the Slurm REST API (slurmrestd), with a token of the
# requesting user, polls the job and collects the STAC results. It reuses the stage-in
# and stage-out wrapping of zoo-calrissian-runner, which is already in the base image.
#
# The service template (cookiecutter) is not part of the image. The chart clones it from
# cookiecutter.templateUrl (values-zoo.yaml).
ARG ZOO_IMAGE=zooproject/zoo-project:dru-19f3c4eed7c9ec9d1f0375bbe59f9d204a42bd3a
FROM ${ZOO_IMAGE}

ARG RUNNER_REPO=https://github.com/Vorkosik/zoo-slurm.git
ARG RUNNER_REF=v0.1.0

USER root
# --no-deps: every dependency is in the base image (zoo-runner-common, zoo-calrissian-runner,
# requests, boto3, PyJWT, PyYAML, loguru); the import check below fails the build otherwise.
RUN pip install --no-cache-dir --no-deps "zoo-slurm-runner @ git+${RUNNER_REPO}@${RUNNER_REF}#subdirectory=runner" \
 && python3 -c "import zoo_slurm_runner; print(zoo_slurm_runner.__file__)"
USER www-data

LABEL org.opencontainers.image.title="zoo-project-slurm" \
      org.opencontainers.image.description="ZOO-Project DRU with a runner that executes CWL Application Packages as Slurm jobs" \
      org.opencontainers.image.source="https://github.com/EOEPCA/eoepca-plus"
