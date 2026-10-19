ARG API_IMAGE=ghcr.io/tommmdl/docker-lab@sha256:ae2e93fdbab7bc912897e6524b3e17b982e97cfb29bcb4fc36d9c014d615eb91
FROM python:3.13.16-alpine3.24@sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a AS dependencies
COPY requirements.lock /tmp/tracing-requirements.lock
RUN pip install --only-binary=:all: --no-cache-dir --target=/opt/tracing -r /tmp/tracing-requirements.lock
FROM ${API_IMAGE}
COPY --from=dependencies /opt/tracing /usr/local/lib/python3.13/site-packages/
COPY traced.py /app/traced.py
USER 10001:10001
CMD ["sh", "-c", "python migrate.py && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - traced:app"]
