"""Initialize tracing inside each Gunicorn worker; app routes remain upstream."""
import atexit
import json
import logging
import sys
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from flask import request
from server import app

provider=TracerProvider(resource=Resource.create({}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(),schedule_delay_millis=500))
trace.set_tracer_provider(provider)
atexit.register(provider.shutdown)
PsycopgInstrumentor().instrument()
FlaskInstrumentor().instrument_app(app,excluded_urls='healthz,readyz')
logger=logging.getLogger('notes.trace')
logger.setLevel(logging.INFO)
logger.propagate=False
handler=logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

@app.after_request
def correlate(response):
    context=trace.get_current_span().get_span_context()
    if context.is_valid:
        trace_id=f'{context.trace_id:032x}'
        response.headers['X-Trace-Id']=trace_id
        logger.info(json.dumps({'event':'http_request','trace_id':trace_id,'span_id':f'{context.span_id:016x}','method':request.method,'route':request.url_rule.rule if request.url_rule else 'unmatched','status':response.status_code}))
    return response
