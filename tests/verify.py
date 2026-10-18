#!/usr/bin/env python3
"""Follow real requests through Flask, Psycopg, Collector, Tempo and Grafana."""
import base64,json,sys,time,urllib.error,urllib.parse,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from client import ROOT,api,forward,k,obj,password,wait
import fcntl
(ROOT/'.local').mkdir(exist_ok=True)
lock=(ROOT/'.local/verification.lock').open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit('Another tracing verification is running in this checkout.')
checks=[]
trace_id=uuid.uuid4().hex
parent='0123456789abcdef'
def check(label,value):
    assert value,label
    checks.append(label);print('OK:',label,flush=True)
def attrs(items):return {a['key']:int(a['value']['intValue']) if 'intValue' in a['value'] else next(iter(a['value'].values())) for a in items}
def hexid(value):
    if len(value) in [16,32] and all(c in '0123456789abcdefABCDEF' for c in value):return value.lower()
    return base64.b64decode(value).hex()
def batches(result):return result.get('batches',result.get('resourceSpans',result.get('trace',{}).get('resourceSpans',[])))
def spans(result):return [span for batch in batches(result) for scope in batch.get('scopeSpans',batch.get('instrumentationLibrarySpans',[])) for span in scope.get('spans',[])]
def dbspans(result):return [s for s in spans(result) if attrs(s.get('attributes',[])).get('db.system',attrs(s.get('attributes',[])).get('db.system.name'))=='postgresql']
def trace(base,identifier):
    try:return api(base,'/api/traces/'+identifier)
    except urllib.error.HTTPError as error:
        if error.code==404:return {}
        raise
with forward('notes-lab','notes-api',80) as app,forward('tracing-lab','tempo',3200) as tempo,forward('monitoring-lab','grafana',3000) as grafana,forward('logging-lab','loki',3100) as loki:
    wait(lambda:api(tempo,'/ready'))
    headers={'traceparent':f'00-{trace_id}-{parent}-01'}
    with urllib.request.urlopen(urllib.request.Request(app+'/notes',headers=headers),timeout=15) as response:
        check('Existing notes endpoint still returns 200',response.status==200)
        check('W3C traceparent is preserved in response trace ID',response.headers.get('X-Trace-Id')==trace_id)
    wait(lambda:len(dbspans(trace(tempo,trace_id)))>0)
    result=trace(tempo,trace_id)
    server=[s for s in spans(result) if s.get('kind') in [2,'SPAN_KIND_SERVER']]
    check('Tempo stores the Flask server span',len(server)==1)
    check('Server span keeps the caller parent span ID',hexid(server[0]['parentSpanId'])==parent)
    check('Database client spans are present',bool(dbspans(result)))
    check('Database span is a child of the server span',any(hexid(s.get('parentSpanId',''))==hexid(server[0]['spanId']) for s in dbspans(result)))
    check('Service resource identifies the API',any(attrs(b.get('resource',{}).get('attributes',[])).get('service.name')=='notes-api' for b in batches(result)))
    check('Trace contains a SELECT operation',any('SELECT' in str(attrs(s.get('attributes',[]))) for s in dbspans(result)))
    # Create/delete only our own record; titles must not be copied into trace attributes.
    secret_title='tracing-test-'+uuid.uuid4().hex
    post_trace=uuid.uuid4().hex
    note=None
    try:
        request=urllib.request.Request(app+'/notes',data=json.dumps({'title':secret_title}).encode(),headers={'Content-Type':'application/json','traceparent':f'00-{post_trace}-{parent}-01'},method='POST')
        with urllib.request.urlopen(request,timeout=15) as response:
            note=json.load(response);check('Instrumented app still creates notes',response.status==201)
        wait(lambda:len(dbspans(trace(tempo,post_trace)))>0)
        check('Note title is not copied into trace data',secret_title not in json.dumps(trace(tempo,post_trace)))
    finally:
        if note:
            with urllib.request.urlopen(urllib.request.Request(app+'/notes/'+str(note['id']),method='DELETE'),timeout=15) as response:check('Only the test note is removed',response.status==204)
    bad_trace=uuid.uuid4().hex
    try:urllib.request.urlopen(urllib.request.Request(app+'/__tracing_missing__',headers={'traceparent':f'00-{bad_trace}-{parent}-01'}),timeout=15)
    except urllib.error.HTTPError as error:check('Unknown route remains an expected 404',error.code==404)
    wait(lambda:len(spans(trace(tempo,bad_trace)))>0)
    check('HTTP 404 is visible in span attributes',any(attrs(s.get('attributes',[])).get('http.status_code',attrs(s.get('attributes',[])).get('http.response.status_code'))==404 for s in spans(trace(tempo,bad_trace))))
    auth=password()
    check('Tempo datasource passes Grafana health check',api(grafana,'/api/datasources/uid/tracing-tempo/health',auth=auth)['status']=='OK')
    now=int(time.time()*1000)
    response=api(grafana,'/api/ds/query','POST',{'from':str(now-900000),'to':str(now),'queries':[{'refId':'A','datasource':{'type':'tempo','uid':'tracing-tempo'},'queryType':'traceId','query':trace_id}]},auth)['results']['A']
    check('Grafana returns trace frames',not response.get('error') and bool(response.get('frames')))
    # Verify correlation using the labels configured for Tempo traces-to-logs.
    logql='{namespace="notes-lab",app="notes-api"} |= "'+trace_id+'"'
    def correlated():
        params=urllib.parse.urlencode({'query':logql,'start':str(time.time_ns()-900_000_000_000),'end':str(time.time_ns()),'limit':100})
        return api(loki,'/loki/api/v1/query_range?'+params)['data']['result']
    wait(correlated)
    check('Same trace ID appears in centralized application logs',bool(correlated()))
    for uid in ['prometheus','logging-loki']:
        check('Existing datasource '+uid+' remains healthy',api(grafana,'/api/datasources/uid/'+uid+'/health',auth=auth)['status']=='OK')
    source=api(grafana,'/api/datasources/uid/tracing-tempo',auth=auth)
    check('Tempo traces-to-logs points to the existing Loki datasource',source['jsonData']['tracesToLogsV2']['datasourceUid']=='logging-loki')
(ROOT/'.local/trace-sample.json').write_text(json.dumps(result,indent=2)+'\n')
output={'executed_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks_passed':len(checks),'checks':checks,'trace_id':trace_id,'span_count':len(spans(result)),'database_span_count':len(dbspans(result)),'app_image':json.loads((ROOT/'config/app-image.json').read_text()),'versions':json.loads((ROOT/'config/images.json').read_text()),'scope':'Actual instrumented Flask/Psycopg requests over OTLP HTTP through Collector to Tempo; Grafana query and Loki correlation; not a synthetic OTLP push','final_state':'API available; test note deleted; Tempo and Collector running; existing datasources preserved'}
(ROOT/'.local/verification.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
