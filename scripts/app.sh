#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if bash scripts/k.sh -n argocd get application notes >/dev/null 2>&1; then
  echo 'Application is managed by Argo CD: update argocd-lab/workloads/notes/api.yaml through Git.' >&2
  exit 1
fi
bash scripts/k.sh -n notes-lab patch deployment notes-api --type=strategic --patch-file application/patch.yaml
bash scripts/k.sh -n notes-lab rollout status deployment/notes-api --timeout=180s
