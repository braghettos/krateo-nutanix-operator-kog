#!/usr/bin/env bash
# Create/refresh the ConfigMaps that hold the OAS slices referenced by each
# RestDefinition's spec.oasPath (configmap://<ns>/<name>/<file>).
#
# Usage: ./scripts/make-configmaps.sh [namespace]
set -euo pipefail

NS="${1:-nutanix-system}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# configmap-name : path-to-oas-file  (name must match spec.oasPath in the RestDefinition)
declare -a PAIRS=(
  "nutanix-vm-oas:${ROOT}/oas/vmm/vm.yaml"
  "nutanix-image-oas:${ROOT}/oas/vmm/image.yaml"
  "nutanix-subnet-oas:${ROOT}/oas/networking/subnet.yaml"
  "nutanix-cluster-oas:${ROOT}/oas/clustermgmt/cluster.yaml"
  "nutanix-category-oas:${ROOT}/oas/prism/category.yaml"
)

kubectl get namespace "$NS" >/dev/null 2>&1 || kubectl create namespace "$NS"

for pair in "${PAIRS[@]}"; do
  name="${pair%%:*}"
  file="${pair#*:}"
  echo ">> ConfigMap ${name} <- ${file}"
  # --dry-run|apply makes this idempotent (create or update).
  kubectl create configmap "$name" \
    --namespace "$NS" \
    --from-file="$(basename "$file")=$file" \
    --dry-run=client -o yaml | kubectl apply -f -
done

echo "Done. ConfigMaps in namespace ${NS}:"
kubectl get configmap -n "$NS" | grep -E 'nutanix-.*-oas' || true
