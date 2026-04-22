# app/services/console_service.py

import uuid
import redis
from datetime import datetime, timedelta

class ConsoleService:
    def __init__(self, db: Session):
        self.db = db
        # Use Redis for token storage (fast, auto-expiry)
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    def create_console_session(self, vm_id: int, user_id: int) -> Dict[str, Any]:
        """Create a one-time console session with random UUID token"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        # Generate random UUID token
        token = str(uuid.uuid4())
        
        # Get VNC port from libvirt
        with LibvirtService() as libvirt:
            console_info = libvirt.get_console_url(db_vm.name)
            vnc_port = console_info.get('port', 5900)
        
        # Store in Redis with 5 minute expiry
        session_data = {
            'vm_name': db_vm.name,
            'vnc_port': vnc_port,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.redis.hset(f"console:session:{token}", mapping=session_data)
        self.redis.expire(f"console:session:{token}", 300)  # 5 minutes
        
        # Return WebSocket URL with token in path
        return {
            'url': f"wss://{os.getenv('CONSOLE_HOST')}/console/{token}",
            'token': token,
            'expires_in': 300
        }
    
    def validate_console_token(self, token: str) -> Optional[Dict]:
        """Validate console token and return session data"""
        session = self.redis.hgetall(f"console:session:{token}")
        if not session:
            return None
        
        # Token is valid - delete it (ONE-TIME USE)
        self.redis.delete(f"console:session:{token}")
        
        return session