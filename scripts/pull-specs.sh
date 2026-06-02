#!/usr/bin/env bash
# Pull the AUTHORITATIVE, version-exact Nutanix v4 OpenAPI specs from a live
# Prism Central (e.g. a Community Edition instance) into oas/_raw/.
#
# Nutanix does NOT publish these specs as downloadable files - the running PC is
# the source of truth. After pulling, trim each raw spec down to the resource +
# verbs you need (the slices under oas/<ns>/ are hand-trimmed starting points).
#
# Usage:
#   PC_HOST=10.0.0.10:9440 PC_USER=admin PC_PASS='secret' ./scripts/pull-specs.sh
#
# Notes:
#   * -k disables TLS verification (CE uses a self-signed cert). Drop it in prod.
#   * The exact spec endpoint path can vary by PC build. This script tries the
#     common locations and reports which worked; adjust if your build differs.
set -euo pipefail

PC_HOST="${PC_HOST:?set PC_HOST, e.g. 10.0.0.10:9440}"
PC_USER="${PC_USER:?set PC_USER}"
PC_PASS="${PC_PASS:?set PC_PASS}"
OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/oas/_raw"
mkdir -p "$OUT"

# namespace : version  (match these to your PC build via the API explorer)
declare -a NS=(
  "vmm:v4.1"
  "networking:v4.0"
  "clustermgmt:v4.0"
  "prism:v4.0"
  "iam:v4.0"
)

curl_pc() { curl -sk -u "${PC_USER}:${PC_PASS}" -w '\n%{http_code}' "$@"; }

for entry in "${NS[@]}"; do
  ns="${entry%%:*}"; ver="${entry#*:}"
  echo "== ${ns} ${ver} =="
  got=""
  # Candidate spec-document locations seen across PC builds:
  for path in \
    "https://${PC_HOST}/api/${ns}/${ver}/openapi.json" \
    "https://${PC_HOST}/api/${ns}/${ver}/api-docs" \
    "https://${PC_HOST}/api/${ns}/${ver}/swagger.json" \
    "https://${PC_HOST}/api/${ns}/${ver}/spec" ; do
    resp="$(curl_pc "$path" || true)"
    code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
    if [[ "$code" == "200" && -n "$body" ]]; then
      echo "$body" > "${OUT}/${ns}-${ver}.json"
      echo "  OK  -> oas/_raw/${ns}-${ver}.json  (from ${path})"
      got="yes"; break
    fi
  done
  [[ -z "$got" ]] && echo "  !!  no spec endpoint responded 200 - check version/build or use the PC API explorer to find the spec URL"
done

echo
echo "Raw specs in ${OUT}:"
ls -la "$OUT" 2>/dev/null || true
