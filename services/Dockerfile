FROM python:3.13-slim
ARG SERVICE_MODULE=services.project_npi.app:app
ARG ENABLE_LLM=false
ENV SERVICE_MODULE=${SERVICE_MODULE} PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/requirements.txt services/requirements.lock services/requirements-llm.txt /app/services/
RUN pip install --no-cache-dir -r services/requirements.txt && \
    if [ "$ENABLE_LLM" = "true" ]; then pip install --no-cache-dir -r services/requirements-llm.txt; fi && \
    groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY services /app/services
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["sh", "-c", "exec uvicorn \"$SERVICE_MODULE\" --host 0.0.0.0 --port 8000 --no-access-log"]
