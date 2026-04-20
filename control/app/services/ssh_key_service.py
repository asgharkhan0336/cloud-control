"""SSH Key Service - Manages SSH public keys"""

import hashlib
import base64
import struct
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import SSHKey, User

class SSHKeyService:
    def __init__(self, db: Session):
        self.db = db
    
    def _parse_ssh_key(self, public_key: str) -> tuple:
        """
        Parse SSH public key and extract type, key data, and generate fingerprint
        Returns: (key_type, key_bits, fingerprint, key_comment)
        """
        try:
            parts = public_key.strip().split()
            if len(parts) < 2:
                raise ValueError("Invalid SSH key format")
            
            key_type = parts[0]
            key_data = parts[1]
            key_comment = parts[2] if len(parts) > 2 else ""
            
            # Decode base64 key data
            decoded = base64.b64decode(key_data)
            
            # Generate fingerprint (MD5 - legacy, SHA256 - modern)
            md5_fingerprint = hashlib.md5(decoded).hexdigest()
            md5_fingerprint = ':'.join(md5_fingerprint[i:i+2] for i in range(0, len(md5_fingerprint), 2))
            
            sha256_fingerprint = base64.b64encode(hashlib.sha256(decoded).digest()).decode()
            fingerprint = f"SHA256:{sha256_fingerprint.rstrip('=')}"
            
            # Get key bits for RSA keys
            key_bits = 0
            if key_type == "ssh-rsa":
                # Parse RSA key to get bit length
                pos = 0
                # Skip algorithm string
                alg_len = struct.unpack('>I', decoded[pos:pos+4])[0]
                pos += 4 + alg_len
                # Read exponent
                exp_len = struct.unpack('>I', decoded[pos:pos+4])[0]
                pos += 4 + exp_len
                # Read modulus
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
    
    def create_ssh_key(
        self,
        user_id: int,
        name: str,
        public_key: str,
        fingerprint: Optional[str] = None
    ) -> SSHKey:
        """Add a new SSH key for a user"""
        
        # Check if key name already exists for this user
        existing = self.db.query(SSHKey).filter(
            SSHKey.user_id == user_id,
            SSHKey.name == name
        ).first()
        
        if existing:
            raise ValueError(f"SSH key with name '{name}' already exists")
        
        # Parse and validate the key
        key_type, key_bits, generated_fingerprint, key_comment = self._parse_ssh_key(public_key)
        
        # Check if the exact same public key already exists
        existing_key = self.db.query(SSHKey).filter(
            SSHKey.user_id == user_id,
            SSHKey.fingerprint == generated_fingerprint
        ).first()
        
        if existing_key:
            raise ValueError(f"This SSH key already exists with name '{existing_key.name}'")
        
        # Create the SSH key
        ssh_key = SSHKey(
            user_id=user_id,
            name=name,
            public_key=public_key,
            fingerprint=fingerprint or generated_fingerprint,
            key_type=key_type,
            key_bits=key_bits,
            key_comment=key_comment
        )
        
        self.db.add(ssh_key)
        self.db.commit()
        self.db.refresh(ssh_key)
        
        return ssh_key
    
    def list_user_ssh_keys(self, user_id: int) -> List[SSHKey]:
        """List all SSH keys for a user"""
        return self.db.query(SSHKey).filter(SSHKey.user_id == user_id).all()
    
    def get_ssh_key(self, key_id: int, user_id: int) -> Optional[SSHKey]:
        """Get a specific SSH key"""
        return self.db.query(SSHKey).filter(
            SSHKey.id == key_id,
            SSHKey.user_id == user_id
        ).first()
    
    def update_ssh_key(
        self,
        key_id: int,
        user_id: int,
        name: Optional[str] = None
    ) -> SSHKey:
        """Update an SSH key"""
        ssh_key = self.get_ssh_key(key_id, user_id)
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        if name:
            # Check if name already exists
            existing = self.db.query(SSHKey).filter(
                SSHKey.user_id == user_id,
                SSHKey.name == name,
                SSHKey.id != key_id
            ).first()
            
            if existing:
                raise ValueError(f"SSH key with name '{name}' already exists")
            
            ssh_key.name = name
        
        self.db.commit()
        self.db.refresh(ssh_key)
        
        return ssh_key
    
    def delete_ssh_key(self, key_id: int, user_id: int) -> bool:
        """Delete an SSH key"""
        ssh_key = self.get_ssh_key(key_id, user_id)
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        self.db.delete(ssh_key)
        self.db.commit()
        
        return True
    
    def get_ssh_keys_for_vm(self, user_id: int, key_ids: List[int]) -> str:
        """Get SSH keys formatted for cloud-init"""
        keys = self.db.query(SSHKey).filter(
            SSHKey.user_id == user_id,
            SSHKey.id.in_(key_ids)
        ).all()
        
        return '\n'.join([key.public_key for key in keys])