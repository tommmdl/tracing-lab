#!/usr/bin/env python3
import json,sys
from client import ROOT,api,forward,optional,password
source=json.loads((ROOT/'grafana/datasource.json').read_text())
with forward('monitoring-lab','grafana',3000) as base:
    auth=password();existing=optional(base,'/api/datasources/uid/tracing-tempo',auth)
    if existing and (existing['name']!=source['name'] or existing['type']!='tempo'):raise SystemExit('Datasource UID belongs to another resource.')
    if sys.argv[1]=='apply':
        api(base,'/api/datasources/uid/tracing-tempo' if existing else '/api/datasources','PUT' if existing else 'POST',source,auth)
        print('Notes Tempo datasource applied; existing datasources preserved.')
    elif sys.argv[1]=='remove':
        if existing:api(base,'/api/datasources/uid/tracing-tempo','DELETE',auth=auth)
    else:raise SystemExit('Use: python3 scripts/grafana.py apply|remove')
