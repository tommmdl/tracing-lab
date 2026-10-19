#!/usr/bin/env python3
"""A separately selected Alpine API and database inside notes-lab."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];APP=Path(os.environ.get('KUBERNETES_LAB_DIR',str(ROOT.parent/'kubernetes-lab'))).resolve()
def k(*args,data=None):return subprocess.check_output(['bash',str(ROOT/'scripts/k.sh'),'-n','notes-lab',*args],input=data)
def documents(file):
 raw=k('create','--dry-run=client','-f',str(file),'-o','json').decode().strip();items=[]
 while raw:
  d,end=json.JSONDecoder().raw_decode(raw);items.append(d);raw=raw[end:].strip()
 return items
def owned(kind,name):
 process=subprocess.run(['bash',str(ROOT/'scripts/k.sh'),'-n','notes-lab','get',kind,name,'--ignore-not-found=true','-o','json'],capture_output=True,check=True,text=True)
 if process.stdout.strip():
  d=json.loads(process.stdout);assert d['metadata'].get('labels',{}).get('portfolio.devops/lab')=='api-alpine','Refusing to replace/delete an unowned resource: '+name
command=sys.argv[1] if len(sys.argv)>1 else 'status'
if command in ['up','down']:
 for kind,name in [('deployment','notes-api-alpine'),('statefulset','api-alpine-db'),('service','notes-api-alpine'),('service','api-alpine-db')]:owned(kind,name)
if command=='up':
 k('get','secret','notes-db');config=ROOT/'config/api-alpine.json';default_image=json.loads(config.read_text())['traced_image'] if config.exists() else 'docker-lab-api-alpine-otel:local';image=os.environ.get('API_ALPINE_OTEL_IMAGE',default_image)
 db=next(d for d in documents(APP/'manifests/postgres.yaml') if d['kind']=='StatefulSet' and d['metadata']['name']=='postgres-alpine')
 db['metadata']['name']='api-alpine-db';db['spec']['serviceName']='api-alpine-db';db['spec']['selector']['matchLabels']={'app':'api-alpine-db'};db['spec']['template']['metadata']['labels']={'app':'api-alpine-db'}
 api=next(d for d in documents(APP/'manifests/api.yaml') if d['kind']=='Deployment');api['metadata']['name']='notes-api-alpine';api['spec']['replicas']=1;api['spec']['selector']['matchLabels']={'app':'notes-api-alpine'};api['spec']['template']['metadata']['labels']={'app':'notes-api-alpine'}
 container=api['spec']['template']['spec']['containers'][0];container['image']=image;container['imagePullPolicy']='IfNotPresent' if '@sha256:' in image else 'Never';container['env']=[{'name':n,'value':v} for n,v in [('DB_HOST','api-alpine-db'),('OTEL_SERVICE_NAME','notes-api-alpine'),('OTEL_RESOURCE_ATTRIBUTES','service.namespace=notes-lab,deployment.environment.name=alpine-test'),('OTEL_EXPORTER_OTLP_ENDPOINT','http://collector.tracing-lab.svc.cluster.local:4318'),('OTEL_EXPORTER_OTLP_PROTOCOL','http/protobuf')]]
 wait_code="import time\nfrom database import connect\nfor attempt in range(120):\n try:\n  with connect() as c:c.execute('SELECT 1')\n  break\n except Exception:time.sleep(1)\nelse:raise SystemExit('Database readiness timeout')"
 api['spec']['template']['spec']['initContainers']=[{'name':'wait-database','image':image,'imagePullPolicy':container['imagePullPolicy'],'command':['python','-c',wait_code],'env':container['env'],'envFrom':container['envFrom'],'volumeMounts':container['volumeMounts'],'securityContext':container['securityContext'],'resources':{'requests':{'cpu':'50m','memory':'64Mi'},'limits':{'cpu':'1','memory':'256Mi'}}}]
 def service(name,label,port,target,headless=False):
  spec={'selector':{'app':label},'ports':[{'port':port,'targetPort':target}]}
  if headless:spec['clusterIP']='None'
  return {'apiVersion':'v1','kind':'Service','metadata':{'name':name,'namespace':'notes-lab'},'spec':spec}
 resources=[db,api,service('api-alpine-db','api-alpine-db',5432,5432,True),service('notes-api-alpine','notes-api-alpine',80,8000)]
 for d in resources:d['metadata'].setdefault('labels',{})['portfolio.devops/lab']='api-alpine'
 k('apply','-f','-',data=json.dumps({'apiVersion':'v1','kind':'List','items':resources}).encode());k('rollout','status','statefulset/api-alpine-db','--timeout=240s');k('rollout','status','deployment/notes-api-alpine','--timeout=240s')
elif command=='test':
 image=json.loads(k('get','deployment','notes-api-alpine','-o','json'))['spec']['template']['spec']['containers'][0]['image']
 env=dict(os.environ,TRACING_API_SERVICE='notes-api-alpine',TRACING_SERVICE_NAME='notes-api-alpine',TRACING_LOG_APP='notes-api-alpine',TRACING_APP_IMAGE=image,TRACING_EVIDENCE_DIR=str(ROOT/'.local/api-alpine'))
 raise SystemExit(subprocess.call(['python3',str(ROOT/'tests/verify.py')],env=env))
elif command=='down':k('delete','deployment/notes-api-alpine','service/notes-api-alpine','service/api-alpine-db','statefulset/api-alpine-db','--ignore-not-found=true')
elif command=='status':print(k('get','deployment,statefulset,service','-l','portfolio.devops/lab=api-alpine').decode());print(k('get','pvc','data-api-alpine-db-0','--ignore-not-found=true').decode())
else:raise SystemExit('Usage: python3 scripts/alpine-lab.py up|test|status|down')
