#!/usr/bin/env sh
set -eu
BASE_URL="${CENTINELA_BASE_URL:-http://127.0.0.1:8000/api/v1}"
curl --fail --silent "$BASE_URL/health"
curl --fail --silent "$BASE_URL/metrics"

