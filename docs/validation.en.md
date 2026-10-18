# What was exercised

English · [Português](validation.md) · [Back](../README.en.md)

All 19 local checks passed. The [full record](../evidence/local-results.json) includes UTC time, versions, image and trace ID. The [span summary](../evidence/trace-summary.json) shows HTTP/database parent relationships without publishing all attributes.

The test sent a known traceparent to GET /notes. Its ID returned in the response and Tempo received the actual trace through SDK and Collector. The caller parent ID remained on the Flask span and the PostgreSQL span was its child. The trace included a SELECT operation.

A POST created a temporary note and DELETE removed only that note. Its title was absent from the fetched trace. A missing route preserved its expected 404 response and HTTP span attribute. The test queried the trace through Grafana and found the same ID in logs collected through Alloy and Loki. Existing Prometheus and Loki datasources remained healthy.

CI creates a fresh cluster, installs Kubernetes, monitoring and logging projects at fixed revisions, builds the same instrumentation variant, starts Tempo and Collector and repeats verification. CI applies the patch without Argo CD in a disposable cluster. Locally, Argo CD applies `workloads/notes-traced` from Git with self-heal enabled.

Retention over 24 hours, node loss, backup restore, durable Collector queues, span metrics and load were not tested. This does not establish universal data masking, trace persistence after Tempo Pod replacement or lossless delivery during interruptions. Tempo uses one local volume and one replica.

The GitHub Actions result will be recorded after the first run.
