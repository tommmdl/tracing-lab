#!/usr/bin/env python3
"""Portable real OTLP/Tempo checks on a unique disposable Compose stack."""
import base64,json,os,socket,subprocess,time,urllib.request,urllib.error,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];APP=Path(os.environ.get('DOCKER_LAB_DIR',str(ROOT.parent/'docker-lab'))).resolve()
run_id=uuid.uuid4().hex[:10];folder=ROOT/'.local'/('alpine-otlp-'+run_id);folder.mkdir(parents=True)
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
a_port,t_port=port(),port();project='notes-api-alpine-otlp-'+run_id
images=json.loads((ROOT/'config/images.json').read_text())
file=folder/'compose.json';file.write_text(json.dumps({'services':{'api':{'image':os.environ.get('API_ALPINE_OTEL_IMAGE','docker-lab-api-alpine-otel:local'),'environment':{'OTEL_SERVICE_NAME':'notes-api-alpine-ci','OTEL_EXPORTER_OTLP_ENDPOINT':'http://collector:4318','OTEL_EXPORTER_OTLP_PROTOCOL':'http/protobuf'}},'tempo':{'image':images['tempo']['pinned'],'user':'10001:10001','command':['-target=all','-config.file=/etc/tempo.yaml'],'ports':[f'127.0.0.1:{t_port}:3200'],'volumes':[str(ROOT/'config/tempo.yaml')+':/etc/tempo.yaml:ro'],'tmpfs':['/var/tempo:uid=10001,gid=10001,mode=0700,size=128m'],'read_only':True,'cap_drop':['ALL'],'mem_limit':'512m','cpus':1},'collector':{'image':images['collector']['pinned'],'command':['--config=/etc/collector.yaml'],'volumes':[str(ROOT/'config/collector.yaml')+':/etc/collector.yaml:ro'],'read_only':True,'cap_drop':['ALL'],'mem_limit':'256m','cpus':1}}}))
env=dict(os.environ,COMPOSE_PROJECT_NAME=project,COMPOSE_FILE=str(APP/'compose.yaml')+os.pathsep+str(file),API_PORT=str(a_port))
def compose(*args):return subprocess.check_output(['bash',str(APP/'scripts/compose.sh'),*args],env=env)
def get(base,path,body=None,trace_id=None,method=None):
 headers={'Content-Type':'application/json'}
 if trace_id:headers['traceparent']='00-'+trace_id+'-0123456789abcdef-01'
 req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method=method)
 try:r=urllib.request.urlopen(req,timeout=10)
 except urllib.error.HTTPError as e:r=e
 with r:
  raw=r.read();return r.status,dict(r.headers),json.loads(raw) if raw.startswith((b'{',b'[')) else raw.decode()
def wait(fn):
 for _ in range(120):
  try:
   value=fn()
   if value:return value
  except (OSError,ValueError):pass
  time.sleep(1)
 raise AssertionError('Timed out waiting for trace data')
def spans(d):return [s for b in d.get('batches',d.get('resourceSpans',[])) for scope in b.get('scopeSpans',[]) for s in scope.get('spans',[])]
def attrs(s):return {a['key']:(int(a['value']['intValue']) if 'intValue' in a['value'] else next(iter(a['value'].values()))) for a in s.get('attributes',[])}
def dbs(d):return [s for s in spans(d) if attrs(s).get('db.system',attrs(s).get('db.system.name'))=='postgresql']
def hexid(s):return s if len(s) in [16,32] else base64.b64decode(s).hex()
checks=[]
def check(n,ok):assert ok,n;checks.append(n)
try:
 compose('up','-d','--no-build','--wait','--wait-timeout','180');app='http://127.0.0.1:'+str(a_port);tempo='http://127.0.0.1:'+str(t_port)
 wait(lambda:get(tempo,'/ready')[0]==200)
 identifier=uuid.uuid4().hex;status,headers,_=get(app,'/notes',trace_id=identifier)
 check('Instrumented notes endpoint returns 200',status==200);check('Traceparent is preserved',headers.get('X-Trace-Id')==identifier)
 def fetch(i):return get(tempo,'/api/traces/'+i)[2]
 result=wait(lambda:(d if dbs(d) else None) if isinstance(d:=fetch(identifier),dict) else None)
 server=[s for s in spans(result) if s.get('kind') in [2,'SPAN_KIND_SERVER']];check('Tempo stores a server span',len(server)==1);check('Server preserves caller parent',hexid(server[0]['parentSpanId'])=='0123456789abcdef');check('PostgreSQL child span exists',bool(dbs(result)));check('DB span parent matches server',any(hexid(s.get('parentSpanId',''))==hexid(server[0]['spanId']) for s in dbs(result)));check('SELECT operation appears',any('SELECT' in str(attrs(s)) for s in dbs(result)));check('Service name identifies candidate',any(attrs(b.get('resource',{})).get('service.name')=='notes-api-alpine-ci' for b in result.get('batches',result.get('resourceSpans',[]))))
 title='private-fixture-'+uuid.uuid4().hex;post=uuid.uuid4().hex;note=None
 try:
  status,_,note=get(app,'/notes',{'title':title},post);check('Traced API writes a note',status==201)
  written=wait(lambda:(d if dbs(d) else None) if isinstance(d:=fetch(post),dict) else None);check('Note title is not exported',title not in json.dumps(written))
 finally:
  if note:check('Only fixture note is removed',get(app,'/notes/'+str(note['id']),method='DELETE')[0]==204)
 missing=uuid.uuid4().hex;check('Unknown route returns 404',get(app,'/__tracing_missing__',trace_id=missing)[0]==404)
 bad=wait(lambda:(d if spans(d) else None) if isinstance(d:=fetch(missing),dict) else None);check('404 is recorded in spans',any(attrs(s).get('http.status_code',attrs(s).get('http.response.status_code'))==404 for s in spans(bad)))
 output={'checks_passed':len(checks),'checks':checks,'image':os.environ.get('API_ALPINE_OTEL_IMAGE','docker-lab-api-alpine-otel:local'),'trace_id':identifier,'database_spans':len(dbs(result)),'scope':'Actual Flask/Psycopg -> Collector -> Tempo over OTLP HTTP in a disposable Compose stack; no synthetic span injection. Grafana/Loki integration is tested separately.'}
 (ROOT/'.local/alpine-otlp-results.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
finally:compose('down','-v','--remove-orphans')
