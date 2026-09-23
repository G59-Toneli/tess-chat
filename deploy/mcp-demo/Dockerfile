# Servidor MCP mínimo (plano B do ticket 17). Streamable HTTP em :8765/mcp.
FROM python:3.14-slim
RUN pip install --no-cache-dir "mcp==2.2.0" "uvicorn==0.53.0"
WORKDIR /app
COPY server.py .
ENV HOST=0.0.0.0 PORT=8765
EXPOSE 8765
CMD ["python", "server.py"]
