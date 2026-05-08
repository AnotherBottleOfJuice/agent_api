FROM python:3.13-slim
WORKDIR /app
COPY . .

ENV SECRET_KEY=abacaba

ENV DEFAULT_MCP_NAME=Simple-MCP

RUN pip install .
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api_agent.app:app", "--host", "0.0.0.0", "--port", "8000"]