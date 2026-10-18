#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
bash scripts/k.sh -n argocd get application notes >/dev/null
case "${1:-apply}" in
  apply) manifest=application/argocd.yaml ;;
  restore) manifest=application/argocd-base.yaml ;;
  *) echo 'Use: bash scripts/argocd.sh apply|restore' >&2; exit 1 ;;
esac
bash scripts/k.sh -n argocd apply -f "$manifest"
bash scripts/k.sh -n argocd annotate application notes argocd.argoproj.io/refresh=hard --overwrite
python3 - "${1:-apply}" <<'PY'
import json,subprocess,sys,time
traced=len(sys.argv)<2 or sys.argv[1]!='restore'
expected=json.load(open('config/app-image.json'))['image'] if traced else json.load(open('config/app-image.json'))['base_image']
for _ in range(90):
    image=subprocess.check_output(['bash','scripts/k.sh','-n','notes-lab','get','deployment','notes-api','-o','jsonpath={.spec.template.spec.containers[0].image}'],text=True)
    if image==expected:break
    time.sleep(2)
else:raise SystemExit('Argo CD did not apply the selected image in time')
PY
bash scripts/k.sh -n notes-lab rollout status deployment/notes-api --timeout=180s
bash scripts/k.sh -n argocd wait application/notes --for=jsonpath='{.status.health.status}'=Healthy --timeout=120s
