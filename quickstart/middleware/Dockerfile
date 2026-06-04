# Nutanix v4 translating proxy — stdlib-only, no third-party deps.
FROM python:3.11-slim
WORKDIR /app
COPY nutanix_v4_proxy.py /app/nutanix_v4_proxy.py
ENV PORT=8080 TLS_VERIFY=false TASK_TIMEOUT_S=180 LOG_LEVEL=INFO
EXPOSE 8080
USER 65534:65534
ENTRYPOINT ["python", "/app/nutanix_v4_proxy.py"]
