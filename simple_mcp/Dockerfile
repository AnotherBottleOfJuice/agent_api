FROM python:3.13-slim
WORKDIR /app
COPY . .

ENV SIMPLE_MCP_NAME=Simple-MCP

RUN pip install .
EXPOSE 8000

CMD ["python", \ 
    "-m", \
    "uvicorn", \
    "simple_mcp.main:app", \
    "--host", \
    "0.0.0.0", \
    "--port", \
    "8000", \
    "--proxy-headers", \
    "--forwarded-allow-ips='*'" \
]