"""Floating IPs API - Public IP Assignment Management"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.services.floating_ip_service import FloatingIPService

router = APIRouter(prefix="/api/v1/floating-ips", tags=["Floating IPs"])

# ============================================
# Pydantic Schemas
# ============================================

class FloatingIPResponse(BaseModel):
    id: int
    ip_address: str
    subnet_id: int
    vm_id: Optional[int]
    vm_name: Optional[str]
    is_allocated: bool
    allocated_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class FloatingIPAssignRequest(BaseModel):
    vm_id: int
    subnet_id: Optional[int] = None

class FloatingIPReleaseRequest(BaseModel):
    ip_address: str

# ============================================
# Floating IP Endpoints
# ============================================

@router.get("/available", response_model=List[FloatingIPResponse])
async def get_available_floating_ips(
    subnet_id: Optional[int] = Query(None, description="Filter by subnet"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available floating IPs"""
    service = FloatingIPService(db)
    return service.get_available_ips(subnet_id, current_user.id)

@router.get("/", response_model=List[FloatingIPResponse])
async def list_floating_ips(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all floating IPs (allocated and available)"""
    service = FloatingIPService(db)
    return service.list_user_floating_ips(current_user.id)

@router.post("/assign", response_model=FloatingIPResponse)
async def assign_floating_ip(
    request: FloatingIPAssignRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign a floating IP to a VM"""
    try:
        service = FloatingIPService(db)
        return service.assign_floating_ip(
            vm_id=request.vm_id,
            subnet_id=request.subnet_id,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign floating IP: {str(e)}")

@router.post("/release")
async def release_floating_ip(
    request: FloatingIPReleaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Release a floating IP"""
    try:
        service = FloatingIPService(db)
        return service.release_floating_ip(request.ip_address, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to release floating IP: {str(e)}")

@router.get("/{ip_address}", response_model=FloatingIPResponse)
async def get_floating_ip(
    ip_address: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get floating IP details"""
    service = FloatingIPService(db)
    fip = service.get_floating_ip(ip_address, current_user.id)
    if not fip:
        raise HTTPException(status_code=404, detail="Floating IP not found")
    return fip