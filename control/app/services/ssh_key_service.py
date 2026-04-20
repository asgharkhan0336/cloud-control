"""SSH Key Service - SSH Public Key Management"""

import hashlib
import base64
import struct
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import SSHKey, User

class SSHKeyService:
    def __init__(self, db: Session):
        self.db = db
    
    def _parse_ssh_key(self, public_key: str) -> tuple:
        """Parse SSH public key and generate fingerprint"""
        try:
            parts = public_key.strip().split()
            if len(parts) < 2:
                raise ValueError("Invalid SSH key format")
            
            key_type = parts[0]
            key_data = parts[1]
            key_comment = parts[2] if len(parts) > 2 else ""
            
            decoded = base64.b64decode(key_data)
            
            sha256_fingerprint = base64.b64encode(
                hashlib.sha256(decoded).digest()
            ).decode()
            fingerprint = f"SHA256:{sha256_fingerprint.rstrip('=')}"
            
            key_bits = 0
            if key_type == "ssh-rsa":
                pos = 0
                alg_len = struct.unpack('>I', decoded[pos:pos+4])[0]
                pos += 4 + alg_len
                exp_len = struct.unpack('>I', decoded[pos:pos+4])[0]
                pos += 4 + exp_len
                mod_len = struct.unpack('>I', decoded[pos:pos+4])[0]
                key_bits = mod_len * 8
            elif key_type == "ecdsa-sha2-nistp256":
                key_bits = 256
            elif key_type == "ecdsa-sha2-nistp384":
                key_bits = 384
            elif key_type == "ecdsa-sha2-nistp521":
                key_bits = 521
            elif key_type == "ssh-ed25519":
                key_bits = 256
            
            return key_type, key_bits, fingerprint, key_comment
            
        except Exception as e:
            raise ValueError(f"Failed to parse SSH key: {str(e)}")
    
    def create_ssh_key(self, user_id: int, name: str, public_key: str) -> Dict:
        """Add a new SSH key for a user"""
        
        existing = self.db.query(SSHKey).filter(
            and_(SSHKey.user_id == user_id, SSHKey.name == name)
        ).first()
        
        if existing:
            raise ValueError(f"SSH key with name '{name}' already exists")
        
        key_type, key_bits, fingerprint, key_comment = self._parse_ssh_key(public_key)
        
        existing_key = self.db.query(SSHKey).filter(
            and_(SSHKey.user_id == user_id, SSHKey.fingerprint == fingerprint)
        ).first()
        
        if existing_key:
            raise ValueError(f"This SSH key already exists with name '{existing_key.name}'")
        
        ssh_key = SSHKey(
            user_id=user_id,
            name=name,
            public_key=public_key,
            fingerprint=fingerprint,
            key_type=key_type,
            key_bits=key_bits,
            key_comment=key_comment
        )
        
        self.db.add(ssh_key)
        self.db.commit()
        self.db.refresh(ssh_key)
        
        return self._format_ssh_key(ssh_key)
    
    def list_user_ssh_keys(self, user_id: int) -> List[Dict]:
        """List all SSH keys for a user"""
        keys = self.db.query(SSHKey).filter(SSHKey.user_id == user_id).all()
        return [self._format_ssh_key(key) for key in keys]
    
    def get_ssh_key(self, key_id: int, user_id: int) -> Optional[Dict]:
        """Get a specific SSH key"""
        key = self.db.query(SSHKey).filter(
            and_(SSHKey.id == key_id, SSHKey.user_id == user_id)
        ).first()
        
        if not key:
            return None
        
        return self._format_ssh_key(key)
    
    def update_ssh_key(self, key_id: int, user_id: int, name: Optional[str] = None) -> Dict:
        """Update an SSH key's name"""
        ssh_key = self.db.query(SSHKey).filter(
            and_(SSHKey.id == key_id, SSHKey.user_id == user_id)
        ).first()
        
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        if name:
            existing = self.db.query(SSHKey).filter(
                and_(SSHKey.user_id == user_id, SSHKey.name == name, SSHKey.id != key_id)
            ).first()
            
            if existing:
                raise ValueError(f"SSH key with name '{name}' already exists")
            
            ssh_key.name = name
        
        self.db.commit()
        self.db.refresh(ssh_key)
        
        return self._format_ssh_key(ssh_key)
    
    def delete_ssh_key(self, key_id: int, user_id: int) -> bool:
        """Delete an SSH key"""
        ssh_key = self.db.query(SSHKey).filter(
            and_(SSHKey.id == key_id, SSHKey.user_id == user_id)
        ).first()
        
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        self.db.delete(ssh_key)
        self.db.commit()
        
        return True
    
    def _format_ssh_key(self, key: SSHKey) -> Dict:
        """Format SSH key for API response"""
        return {
            "id": key.id,
            "name": key.name,
            "fingerprint": key.fingerprint,
            "key_type": key.key_type,
            "key_bits": key.key_bits,
            "created_at": key.created_at
        }