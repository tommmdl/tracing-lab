#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
image=$(python3 -c 'import json; print(json.load(open("config/app-image.json"))["image"])')
python3 scripts/image.py check
if [[ "${1:-}" != --local ]]; then
  docker pull "$image"
  echo 'Published tracing image ready; the Pod uses this digest with IfNotPresent.'
  exit 0
fi
image=$(python3 -c 'import json; print(json.load(open("config/app-image.json"))["local_build_image"])')
python3 scripts/image.py check
mkdir -p .local/docker/cli-plugins
if ! docker buildx version >/dev/null 2>&1; then
  python3 - <<'PY'
import hashlib,urllib.request
from pathlib import Path
version='v0.38.0'
asset=f'buildx-{version}.linux-amd64'
base=f'https://github.com/docker/buildx/releases/download/{version}'
target=Path('.local/docker/cli-plugins/docker-buildx')
if not target.exists():
    data=urllib.request.urlopen(base+'/'+asset,timeout=90).read()
    checks=urllib.request.urlopen(base+'/checksums.txt',timeout=30).read().decode()
    expected=next(line.split()[0] for line in checks.splitlines() if line.split()[-1].lstrip('*')==asset)
    assert hashlib.sha256(data).hexdigest()==expected,'Buildx checksum mismatch'
    target.write_bytes(data);target.chmod(0o755)
PY
  docker --config "$PWD/.local/docker" buildx build --platform linux/amd64 --provenance=false --load --tag "$image" instrumentation
else
  docker buildx build --platform linux/amd64 --provenance=false --load --tag "$image" instrumentation
fi
LAB=${KUBERNETES_LAB_DIR:-$PWD/../kubernetes-lab}
"$LAB/.local/bin/kind" load docker-image --name devops-notes "$image"
