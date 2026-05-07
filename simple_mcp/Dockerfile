FROM python:3.13-slim
WORKDIR /app
COPY . .

ENV SIMPLE_MCP_TOKEN = 'abacaba'
ENV SIMPLE_MCP_NAME = 'Simple-MCP'

RUN pip install .
EXPOSE 8015

CMD [python, "-m", "uvicorn", "simple_mcp.main:app", "--port", "8015"]