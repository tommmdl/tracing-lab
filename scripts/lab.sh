#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
case "${1:-status}" in
  up)
    bash scripts/k.sh -n notes-lab get deployment notes-api >/dev/null
    bash scripts/k.sh -n monitoring-lab get deployment grafana >/dev/null
    bash scripts/k.sh apply -k .
    for name in tempo collector; do bash scripts/k.sh rollout status "deployment/$name" --timeout=240s; done
    python3 scripts/grafana.py apply
    ;;
  status) bash scripts/k.sh get deploy,pods,svc,pvc ;;
  down)
    # Restore the app through Git first: never leave it exporting to a removed endpoint.
    image=$(bash scripts/k.sh -n notes-lab get deploy notes-api -o jsonpath='{.spec.template.spec.containers[0].image}')
    if [[ "$image" == tracing-lab-api:* ]]; then
      echo 'Restore the application through argocd-lab before deleting tracing-lab.' >&2; exit 1
    fi
    python3 scripts/grafana.py remove
    bash scripts/k.sh delete namespace tracing-lab --ignore-not-found
    ;;
  *) echo 'Use: bash scripts/lab.sh up|status|down' >&2; exit 1 ;;
esac
