#!/bin/sh
set -eu

BASE_URL="${STAC_BASE_URL:-https://eoapi.rke2.deploybox.co.uk/stac}"
TMP_DIR="${TMP_DIR:-/tmp/synthetic-api-check}"
ITEMS_LIMIT="${SYNTHETIC_API_CHECK_ITEMS_LIMIT:-3}"
SEARCH_LIMIT="${SYNTHETIC_API_CHECK_SEARCH_LIMIT:-3}"
SLEEP_SECONDS="${SYNTHETIC_API_CHECK_SLEEP_SECONDS:-10}"

mkdir -p "${TMP_DIR}"

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*"
}

extract_json_number() {
  key="$1"
  file="$2"
  value="$(grep -o "\"${key}\": [0-9][0-9]*" "${file}" | head -n1 | awk '{print $2}' || true)"
  if [ -n "${value}" ]; then
    printf '%s\n' "${value}"
  else
    printf '0\n'
  fi
}

extract_first_collection_id() {
  file="$1"
  grep -o '"id": "[^"]*"' "${file}" | head -n1 | sed 's/"id": "\(.*\)"/\1/'
}

run_curl() {
  worker="$1"
  name="$2"
  method="$3"
  url="$4"
  body_file="$5"
  payload="${6:-}"

  log "[worker ${worker}] curl ${method} ${url}"

  if [ "${method}" = "GET" ]; then
    metrics="$(curl -ksS -o "${body_file}" -w 'http_code=%{http_code} time_total=%{time_total} size_download=%{size_download}' "${url}")"
  else
    metrics="$(curl -ksS -o "${body_file}" -w 'http_code=%{http_code} time_total=%{time_total} size_download=%{size_download}' -X POST -H 'content-type: application/json' -d "${payload}" "${url}")"
  fi

  log "[worker ${worker}] ${name} ${metrics}"
}

run_worker() {
  worker="$1"
  collections_file="${TMP_DIR}/${worker}-collections.json"
  items_file="${TMP_DIR}/${worker}-items.json"
  search_file="${TMP_DIR}/${worker}-search.json"

  run_curl "${worker}" collections GET "${BASE_URL}/collections" "${collections_file}"
  collection_count="$(extract_json_number numberReturned "${collections_file}")"
  collection_id="$(extract_first_collection_id "${collections_file}")"
  log "[worker ${worker}] collections returned=${collection_count} selected_collection=${collection_id}"

  if [ -z "${collection_id}" ]; then
    log "[worker ${worker}] no collection id discovered"
    return 1
  fi

  run_curl "${worker}" items GET "${BASE_URL}/collections/${collection_id}/items?limit=${ITEMS_LIMIT}" "${items_file}"
  items_returned="$(extract_json_number numberReturned "${items_file}")"
  items_matched="$(extract_json_number numberMatched "${items_file}")"
  log "[worker ${worker}] items returned=${items_returned} matched=${items_matched} collection=${collection_id}"

  search_payload="$(printf '{"collections":["%s"],"limit":%s}' "${collection_id}" "${SEARCH_LIMIT}")"
  run_curl "${worker}" search POST "${BASE_URL}/search" "${search_file}" "${search_payload}"
  search_returned="$(extract_json_number numberReturned "${search_file}")"
  search_matched="$(extract_json_number numberMatched "${search_file}")"
  log "[worker ${worker}] search returned=${search_returned} matched=${search_matched} collection=${collection_id}"
}

case "${ITEMS_LIMIT}" in
  ''|*[!0-9]*|0)
    log "Invalid SYNTHETIC_API_CHECK_ITEMS_LIMIT=${ITEMS_LIMIT}, using 3"
    ITEMS_LIMIT=3
    ;;
esac

case "${SEARCH_LIMIT}" in
  ''|*[!0-9]*|0)
    log "Invalid SYNTHETIC_API_CHECK_SEARCH_LIMIT=${SEARCH_LIMIT}, using 3"
    SEARCH_LIMIT=3
    ;;
esac

case "${SLEEP_SECONDS}" in
  ''|*[!0-9]*)
    log "Invalid SYNTHETIC_API_CHECK_SLEEP_SECONDS=${SLEEP_SECONDS}, using 10"
    SLEEP_SECONDS=10
    ;;
esac

log "Starting synthetic API check against ${BASE_URL}"
log "Run configuration items_limit=${ITEMS_LIMIT} search_limit=${SEARCH_LIMIT} sleep_seconds=${SLEEP_SECONDS}"

while true; do
  run_worker "pod-${HOSTNAME:-synthetic-api-check}"
  log "Synthetic API check cycle complete; sleeping ${SLEEP_SECONDS}s"
  sleep "${SLEEP_SECONDS}"
done
