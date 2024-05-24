#!/usr/bin/env bash

ORIG_DIR="$(pwd)"
cd "$(dirname "$0")"
BIN_DIR="$(pwd)"

onExit() {
  cd "${ORIG_DIR}"
}
trap onExit EXIT

for f in "$(find -name 'ss-*.sh')"; do
  echo -n "Running ${f}... "
  "${f}"
  echo "[done]"
done
