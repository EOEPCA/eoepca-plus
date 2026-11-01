#!/bin/sh
set -eu

PARTITION="${SYNTHETIC_SLURM_CHECK_PARTITION:-all}"
SLEEP_SECONDS="${SYNTHETIC_SLURM_CHECK_SLEEP_SECONDS:-60}"
STATE_DIR="${SYNTHETIC_SLURM_CHECK_STATE_DIR:-/tmp/synthetic-slurm-check}"
HEALTH_FILE="${STATE_DIR}/healthy"
SACKD_SOCKET="${SYNTHETIC_SLURM_CHECK_SACKD_SOCKET:-/run/slurm/sack.socket}"

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*"
}

case "${SLEEP_SECONDS}" in
  ''|*[!0-9]*|0)
    log "Invalid SYNTHETIC_SLURM_CHECK_SLEEP_SECONDS=${SLEEP_SECONDS}, using 60"
    SLEEP_SECONDS=60
    ;;
esac

mkdir -p "${STATE_DIR}"
rm -f "${HEALTH_FILE}"

log "Starting synthetic Slurm check for partition ${PARTITION}"

while [ ! -S "${SACKD_SOCKET}" ]; do
  log "Waiting for sackd socket ${SACKD_SOCKET}"
  sleep 2
done

check_once() {
  if ! available_nodes="$(sinfo \
    --noheader \
    --partition="${PARTITION}" \
    --states=idle,mix,alloc \
    --format='%N')"; then
    log "Could not query partition ${PARTITION}"
    return 1
  fi

  if [ -z "${available_nodes}" ]; then
    log "No schedulable nodes found in partition ${PARTITION}"
    return 1
  fi

  log "Schedulable nodes: ${available_nodes}"
  if ! worker_hostname="$(srun \
    --partition="${PARTITION}" \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task=1 \
    --mem=64M \
    --immediate=30 \
    --time=00:01:00 \
    hostname)"; then
    log "The synthetic Slurm job failed"
    return 1
  fi

  if [ -z "${worker_hostname}" ]; then
    log "The synthetic Slurm job returned no worker hostname"
    return 1
  fi

  log "Synthetic Slurm job succeeded on ${worker_hostname}"
}

while true; do
  if check_once; then
    touch "${HEALTH_FILE}"
  else
    rm -f "${HEALTH_FILE}"
  fi
  log "Next synthetic Slurm check in ${SLEEP_SECONDS}s"
  sleep "${SLEEP_SECONDS}"
done
