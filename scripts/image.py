#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files=['Dockerfile','requirements.lock','traced.py']
digest=hashlib.sha256()
for name in files:
    digest.update(name.encode()+b'\0'+(root/'instrumentation'/name).read_bytes())
result={'image':'tracing-lab-api:otel-'+digest.hexdigest()[:16],'source_sha256':digest.hexdigest(),'base_image':'ghcr.io/tommmdl/docker-lab@sha256:d8fdaffb99e0ac514b9e031ac9204b89fc2702112d198d1bebedd9d351fd19f0'}
if sys.argv[1]=='write':(root/'config/app-image.json').write_text(json.dumps(result,indent=2)+'\n')
else:assert json.loads((root/'config/app-image.json').read_text())==result,'Image metadata needs regeneration: python3 scripts/image.py write'
