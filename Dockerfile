# Playwright base image includes Chromium and system dependencies for headless scraping.
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MCP_TRANSPORT=sse \
    HOST=0.0.0.0 \
    PORT=10000 \
    MEK_PLAYWRIGHT_HEADLESS=true

COPY pyproject.toml README.md ./
COPY mek_mcp ./mek_mcp

RUN pip install .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"10000\")}/health')" || exit 1

CMD ["python", "-m", "mek_mcp.server"]
