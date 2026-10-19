#!/usr/bin/env python3
"""Keep released image pins separate from local build source fingerprints."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files=['Dockerfile','requirements.lock','traced.py'];digest=hashlib.sha256()
for name in files:digest.update(name.encode()+b'\0'+(root/'instrumentation'/name).read_bytes())
release=json.loads((root/'config/api-alpine.json').read_text())
result={'image':release['traced_image'],'base_image':release['basic_image'],'local_build_image':'tracing-lab-api:otel-alpine-'+digest.hexdigest()[:16],'build_source_sha256':digest.hexdigest(),'publication_workflow':release['publication_workflow'],'scope':'Published digests are release identities; build_source_sha256 fingerprints local build inputs, not a claim that a rebuild is byte-identical to the release.'}
if sys.argv[1]=='write':(root/'config/app-image.json').write_text(json.dumps(result,indent=2)+'\n')
else:assert json.loads((root/'config/app-image.json').read_text())==result,'Run python3 scripts/image.py write after reviewing source or release pin changes'
