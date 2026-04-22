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

@app.websocket("/console/{token}")
async def console_websocket(websocket: WebSocket, token: str):
    """WebSocket proxy for VNC console - token validated from path"""
    await websocket.accept()
    
    # Validate token using ConsoleService
    db = next(get_db())
    console_service = ConsoleService(db)
    session = console_service.validate_console_token(token)
    
    if not session:
        await websocket.close(code=4001, reason="Invalid or expired console token")
        return
    
    vm_name = session.get('vm_name')
    vnc_port = session.get('vnc_port')
    
    if not vm_name or not vnc_port:
        await websocket.close(code=4002, reason="Invalid session data")
        return
    
    vnc_host = os.getenv('VNC_PROXY_HOST', 'localhost')
    vnc_ws_url = f"ws://{vnc_host}:{vnc_port}"
    
    try:
        # Connect to VNC WebSocket
        async with websockets.connect(vnc_ws_url) as vnc_ws:
            
            async def forward_to_vnc():
                """Forward messages from client to VNC"""
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await vnc_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception:
                    pass
            
            async def forward_to_client():
                """Forward messages from VNC to client"""
                try:
                    while True:
                        data = await vnc_ws.recv()
                        await websocket.send_bytes(data)
                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception:
                    pass
            
            # Run both directions concurrently
            await asyncio.gather(
                forward_to_vnc(),
                forward_to_client()
            )
            
    except WebSocketDisconnect:
        print(f"Client disconnected from console: {vm_name}")
    except Exception as e:
        print(f"Console proxy error for {vm_name}: {e}")
        await websocket.close(code=4003, reason="VNC connection failed")
    finally:
        db.close()


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