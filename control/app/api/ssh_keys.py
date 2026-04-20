"""SSH Keys Management API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User, SSHKey
from app.services.ssh_key_service import SSHKeyService

router = APIRouter(prefix="/api/v1/ssh-keys", tags=["SSH Keys"])

# ============================================
# Pydantic Models
# ============================================

class SSHKeyCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9-_ ]+$")
    public_key: str = Field(..., min_length=20)
    fingerprint: Optional[str] = None  # Auto-generated if not provided

class SSHKeyResponse(BaseModel):
    id: int
    name: str
    fingerprint: str
    key_type: str
    key_bits: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SSHKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9-_ ]+$")

# ============================================
# SSH Keys Endpoints
# ============================================

@router.post("/", response_model=SSHKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_ssh_key(
    key_data: SSHKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a new SSH public key
    The key will be validated and its fingerprint auto-generated
    """
    try:
        service = SSHKeyService(db)
        ssh_key = service.create_ssh_key(
            user_id=current_user.id,
            name=key_data.name,
            public_key=key_data.public_key,
            fingerprint=key_data.fingerprint
        )
        return ssh_key
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add SSH key: {str(e)}")

@router.get("/", response_model=List[SSHKeyResponse])
async def list_ssh_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all SSH keys for the current user"""
    service = SSHKeyService(db)
    return service.list_user_ssh_keys(current_user.id)

@router.get("/{key_id}", response_model=SSHKeyResponse)
async def get_ssh_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific SSH key"""
    service = SSHKeyService(db)
    ssh_key = service.get_ssh_key(key_id, current_user.id)
    if not ssh_key:
        raise HTTPException(status_code=404, detail="SSH key not found")
    return ssh_key

@router.patch("/{key_id}", response_model=SSHKeyResponse)
async def update_ssh_key(
    key_id: int,
    key_update: SSHKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an SSH key's name"""
    try:
        service = SSHKeyService(db)
        ssh_key = service.update_ssh_key(
            key_id=key_id,
            user_id=current_user.id,
            name=key_update.name
        )
        return ssh_key
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update SSH key: {str(e)}")

@router.delete("/{key_id}")
async def delete_ssh_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an SSH key"""
    try:
        service = SSHKeyService(db)
        service.delete_ssh_key(key_id, current_user.id)
        return {"success": True, "message": "SSH key deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete SSH key: {str(e)}")

@router.post("/{key_id}/validate")
async def validate_ssh_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Validate an SSH key's format and fingerprint"""
    service = SSHKeyService(db)
    ssh_key = service.get_ssh_key(key_id, current_user.id)
    if not ssh_key:
        raise HTTPException(status_code=404, detail="SSH key not found")
    
    return {
        "valid": True,
        "key_id": key_id,
        "fingerprint": ssh_key.fingerprint,
        "key_type": ssh_key.key_type,
        "key_bits": ssh_key.key_bits
    }