# Use Alibaba mirror on CN servers; override for local dev: --build-arg PYTHON_IMAGE=python:3.12-slim-bookworm
ARG PYTHON_IMAGE=registry.cn-hangzhou.aliyuncs.com/library/python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt

COPY api/ api/
COPY core/ core/
COPY mcp_tools/ mcp_tools/
COPY models/ models/
COPY orchestrator/ orchestrator/
COPY main.py .

RUN mkdir -p /app/data/chroma

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
