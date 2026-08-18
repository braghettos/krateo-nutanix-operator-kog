# Nutanix v4 translating proxy — stdlib-only, no third-party deps.
#
# Released by .github/workflows/release-image.yaml on a bare-semver tag, which passes
# --build-arg VERSION=<tag>. Do not hardcode a version here: this file previously carried
# two (a 0.2.0 in a build hint and a 0.3.0 default) while the chart asked for 0.4.0 and the
# only published image was 0.6.0 — four numbers for one artifact, and the reference between
# chart and image resolved to nothing. The tag is now the single source of that number.
#
# Pinned base (python:3.11-slim-bookworm) by digest for reproducible builds.
FROM python:3.11-slim-bookworm@sha256:8dca233de9f3d9bb410665f00a4da6dd06f331083137e0e98ccf227236fcc438

ARG VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="nutanix-v4-proxy" \
      org.opencontainers.image.description="Translating proxy that lets Krateo rest-dynamic-controller drive the Nutanix Prism Central v4 API" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/krateo-blueprints/krateo-nutanix-operator-kog" \
      org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app
COPY nutanix_v4_proxy.py /app/nutanix_v4_proxy.py

ENV PORT=8080 \
    TLS_VERIFY=false \
    TASK_TIMEOUT_S=180 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 65532:65532

# Liveness from inside the image (k8s probes still hit /healthz over the network).
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["python", "-c", "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/healthz'%os.environ.get('PORT','8080'),timeout=2).read()==b'ok' else 1)"]

ENTRYPOINT ["python", "/app/nutanix_v4_proxy.py"]
