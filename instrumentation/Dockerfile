FROM ghcr.io/tommmdl/docker-lab@sha256:d8fdaffb99e0ac514b9e031ac9204b89fc2702112d198d1bebedd9d351fd19f0
USER root
COPY requirements.lock /tmp/tracing-requirements.lock
RUN pip install --no-cache-dir -r /tmp/tracing-requirements.lock && rm /tmp/tracing-requirements.lock
COPY traced.py /app/traced.py
USER 10001:10001
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "traced:app"]
