FROM python:3.13-slim
WORKDIR /app
COPY . .

ENV SECRET_KEY='abacaba'

ENV SIMPLE_MCP_URL='http://mcp:8015/mcp'
ENV SIMPLE_MCP_TOKEN='abacaba'
ENV SIMPLE_MCP_NAME='Simple-MCP'

RUN pip install .
EXPOSE 4015

CMD ["python", "-m", "uvicorn", "api_agent.app:app", "--host", "0.0.0.0", "--port", "4015"]