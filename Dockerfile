FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY gateonai_mcp_server.py .
# stdio MCP server: no API key, no Redis, no configuration needed
CMD ["python", "gateonai_mcp_server.py"]
