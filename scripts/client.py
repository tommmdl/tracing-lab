"""Local API helpers. Credentials stay in memory; tunnels use temporary ports."""
import base64
import contextlib
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def k(*args):
    return subprocess.check_output(['bash',str(ROOT/'scripts/k.sh'),*args],text=True)
def obj(*args):return json.loads(k(*args,'-o','json'))
def wait(fn,timeout=180):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            if fn():return
        except (urllib.error.URLError,TimeoutError,ConnectionError):pass
        time.sleep(2)
    raise AssertionError('Timed out waiting for '+getattr(fn,'__name__','condition'))
@contextlib.contextmanager
def forward(namespace,service,remote):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen(['bash',str(ROOT/'scripts/k.sh'),'-n',namespace,'port-forward','--address','127.0.0.1','service/'+service,f'{port}:{remote}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        def connected():
            if process.poll() is not None:raise RuntimeError('Port-forward exited for '+service)
            with socket.create_connection(('127.0.0.1',port),timeout=1):return True
        wait(connected,30)
        yield f'http://127.0.0.1:{port}'
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
def password():return base64.b64decode(obj('-n','monitoring-lab','get','secret','grafana-admin')['data']['password']).decode()
def api(base,path,method='GET',payload=None,auth=None):
    headers={"Accept":"application/json"}
    if auth:headers['Authorization']='Basic '+base64.b64encode(('admin:'+auth).encode()).decode()
    data=None
    if payload is not None:
        headers['Content-Type']='application/json';data=json.dumps(payload).encode()
    request=urllib.request.Request(base+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=20) as response:
        body=response.read()
        return json.loads(body) if body.startswith((b'{',b'[')) else body.decode()
def optional(base,path,auth):
    try:return api(base,path,auth=auth)
    except urllib.error.HTTPError as error:
        if error.code==404:return None
        raise
