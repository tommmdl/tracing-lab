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
    python3 - <<'PYGUARD'
import json,subprocess
items=json.loads(subprocess.check_output(['bash','scripts/k.sh','-n','notes-lab','get','deployments','-o','json']))['items']
active=[]
for d in items:
    if d['spec'].get('replicas',1)==0:continue
    for c in d['spec']['template']['spec']['containers']:
        if any(e.get('name')=='OTEL_EXPORTER_OTLP_ENDPOINT' and 'collector.tracing-lab' in e.get('value','') for e in c.get('env',[])):
            active.append(d['metadata']['name'])
if active:raise SystemExit('Restore/stop these traced workloads before removing tracing-lab: '+', '.join(active))
PYGUARD
    python3 scripts/grafana.py remove
    bash scripts/k.sh delete namespace tracing-lab --ignore-not-found
    ;;
  *) echo 'Use: bash scripts/lab.sh up|status|down' >&2; exit 1 ;;
esac
