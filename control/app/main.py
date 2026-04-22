from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import websockets
import os

from app.config import settings
from app.api import vms, host, auth, vpc, subnets, firewall, ssh_keys, floating_ips
from app.services.console_service import ConsoleService
from app.database import get_db

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST routers
app.include_router(auth.router)
app.include_router(vms.router)
app.include_router(host.router)
app.include_router(vpc.router)
app.include_router(subnets.router)
app.include_router(firewall.router)
app.include_router(ssh_keys.router)
app.include_router(floating_ips.router)


# ============================================
# WebSocket Console Proxy (OpenStack Style)
# ============================================


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/api/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )