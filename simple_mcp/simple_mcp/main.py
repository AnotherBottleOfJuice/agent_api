import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware   # ← new import

load_dotenv()

SIMPLE_MCP_NAME = os.getenv('SIMPLE_MCP_NAME')
SIMPLE_MCP_TOKEN = os.getenv('SIMPLE_MCP_TOKEN')

mcp = FastMCP(name=SIMPLE_MCP_NAME)

@mcp.tool()
async def multiply(a: int):
    """Multiplies argument by 2"""
    return a * 2

@mcp.tool()
async def divide(a: int):
    """Divides the given argument by 2 (rounded down)"""
    return a // 2

security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(transport_security=security_settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(status_code=401, content={"detail": "Token missing"})

        try:
            header = auth_header.strip()
            if " " in header:
                token = header.split(" ", 1)[1].strip()
            else:
                token = header
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid token format"})

        if token != SIMPLE_MCP_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)

app.add_middleware(AuthMiddleware)