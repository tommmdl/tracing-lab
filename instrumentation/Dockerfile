FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS dependencies
COPY requirements.lock /tmp/tracing-requirements.lock
RUN pip install --no-cache-dir --target=/opt/tracing -r /tmp/tracing-requirements.lock

FROM ghcr.io/tommmdl/docker-lab@sha256:343f2b23294c09bea9c3250a3b3fd1f95d817acea9db0231dfaaaf406f22fbac
COPY --from=dependencies /opt/tracing /usr/local/lib/python3.13/site-packages/
COPY traced.py /app/traced.py
USER 10001:10001
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "traced:app"]
