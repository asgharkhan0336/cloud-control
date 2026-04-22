# app/api/console.py

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import websockets
import asyncio

router = APIRouter()

@router.websocket("/console/{token}")
async def console_proxy(websocket: WebSocket, token: str):
    """WebSocket proxy for VNC - token in path for security"""
    await websocket.accept()
    
    # Validate token
    console_service = ConsoleService(next(get_db()))
    session = console_service.validate_console_token(token)
    
    if not session:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    try:
        # Connect to VNC WebSocket
        vnc_host = os.getenv('VNC_PROXY_HOST', 'localhost')
        vnc_port = session['vnc_port']
        
        async with websockets.connect(f"ws://{vnc_host}:{vnc_port}") as vnc_ws:
            # Bidirectional proxy
            async def forward_to_vnc():
                try:
                    async for message in websocket.iter_text():
                        await vnc_ws.send(message)
                except:
                    pass
            
            async def forward_to_client():
                try:
                    async for message in vnc_ws:
                        await websocket.send_text(message)
                except:
                    pass
            
            await asyncio.gather(forward_to_vnc(), forward_to_client())
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Console proxy error: {e}")