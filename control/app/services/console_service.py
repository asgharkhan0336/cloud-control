"""Console Service - OpenStack Style One-Time Console Tokens with Redis"""

import uuid
import redis
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.libvirt_service import LibvirtService
from app.models.database import VM


class ConsoleService:
    def __init__(self, db: Session):
        self.db = db
        # Connect to Redis
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
    
    def _get_authorized_vm(self, vm_id: int, user_id: int) -> Optional[VM]:
        """Get VM with authorization check"""
        return self.db.query(VM).filter(
            VM.id == vm_id,
            VM.owner_id == user_id
        ).first()
    
    def create_console_session(self, vm_id: int, user_id: int) -> Dict[str, Any]:
        """Create a one-time console session with random UUID token"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found or access denied")
        
        # Generate random UUID token
        token = str(uuid.uuid4())
        
        # Get VNC port from libvirt
        vnc_port = None
        with LibvirtService() as libvirt:
            console_info = libvirt.get_console_url(db_vm.name)
            vnc_port = console_info.get('port', '5900')
        
        # Store in Redis with 5 minute expiry
        session_key = f"console:session:{token}"
        session_data = {
            'vm_name': db_vm.name,
            'vnc_port': vnc_port,
            'user_id': str(user_id),
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.redis.hset(session_key, mapping=session_data)
        self.redis.expire(session_key, 300)  # 5 minutes
        
        # Return WebSocket URL with token in path
        console_host = os.getenv('CONSOLE_HOST', 'localhost:8000')
        
        return {
            'url': f"ws://{console_host}/console/{token}",
            'token': token,
            'expires_in': 300
        }
    
    def validate_console_token(self, token: str) -> Optional[Dict]:
        """Validate console token and return session data"""
        session_key = f"console:session:{token}"
        
        # Check if session exists
        if not self.redis.exists(session_key):
            return None
        
        # Get session data
        session = self.redis.hgetall(session_key)
        if not session:
            return None
        
        # Token is valid - delete it (ONE-TIME USE)
        self.redis.delete(session_key)
        
        return session
    
    def revoke_console_session(self, token: str) -> bool:
        """Manually revoke a console session"""
        session_key = f"console:session:{token}"
        if self.redis.exists(session_key):
            self.redis.delete(session_key)
            return True
        return False