"""Console Service with websockify proxy"""

import uuid
import redis
import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.libvirt_service import LibvirtService
from app.models.database import VM
from app.config import settings


class ConsoleService:
    def __init__(self, db: Session):
        self.db = db
        self.redis = redis.Redis(
            host=settings.redis_host if hasattr(settings, 'redis_host') else 'localhost',
            port=settings.redis_port if hasattr(settings, 'redis_port') else 6379,
            db=settings.redis_db if hasattr(settings, 'redis_db') else 0,
            decode_responses=True
        )
    
    def _get_authorized_vm(self, vm_id: int, user_id: int) -> Optional[VM]:
        return self.db.query(VM).filter(
            VM.id == vm_id,
            VM.owner_id == user_id
        ).first()
    
    def _find_available_port(self, start_port: int = 6080, end_port: int = 6180) -> int:
        """Find an available port for websockify"""
        import socket
        for port in range(start_port, end_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('0.0.0.0', port))
                    return port
                except OSError:
                    continue
        raise Exception("No available ports for websockify")
    
    def create_console_session(self, vm_id: int, user_id: int) -> Dict[str, Any]:
        """Create a one-time console session with websockify proxy"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found or access denied")
        
        # Check if VM is running
        with LibvirtService() as libvirt:
            vm_info = libvirt.get_vm(db_vm.name)
            if vm_info and vm_info.get('state') != 'running':
                raise ValueError("VM must be running to access console")
            
            # Get VNC port
            console_info = libvirt.get_console_url(db_vm.name)
            vnc_port = console_info.get('port', '5900')
        
        # Generate random UUID token
        token = str(uuid.uuid4())
        
        # Find available port for websockify
        ws_port = self._find_available_port()
        
        # Start websockify for this session
        websockify_cmd = [
            'websockify',
            str(ws_port),
            f'localhost:{vnc_port}'
        ]
        
        # Run websockify in background
        process = subprocess.Popen(
            websockify_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Store session in Redis
        session_key = f"console:session:{token}"
        session_data = {
            'vm_name': db_vm.name,
            'vnc_port': vnc_port,
            'ws_port': str(ws_port),
            'pid': str(process.pid),
            'user_id': str(user_id),
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.redis.hset(session_key, mapping=session_data)
        self.redis.expire(session_key, 300)  # 5 minutes
        
        # Return direct WebSocket URL to websockify
        console_host = settings.console_host.split(':')[0]  # Get IP without port
        
        return {
            'url': f"ws://{console_host}:{ws_port}",
            'token': token,
            'expires_in': 300
        }
    
    def validate_console_token(self, token: str) -> Optional[Dict]:
        """Validate console token"""
        session_key = f"console:session:{token}"
        
        if not self.redis.exists(session_key):
            return None
        
        session = self.redis.hgetall(session_key)
        if not session:
            return None
        
        # Don't delete - websockify needs to stay alive
        # Will be cleaned up by expiry
        
        return session
    
    def cleanup_session(self, token: str):
        """Kill websockify process and remove session"""
        session_key = f"console:session:{token}"
        session = self.redis.hgetall(session_key)
        
        if session and 'pid' in session:
            try:
                os.kill(int(session['pid']), 9)
            except:
                pass
        
        self.redis.delete(session_key)