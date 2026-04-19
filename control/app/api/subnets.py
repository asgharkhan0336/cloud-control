"""Public Subnet API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.auth.auth import get_current_active_user, get_current_superuser
from app.models.database import User
from app.services.subnet_service import PublicSubnetService
from app.services.floating_ip_service import FloatingIPService

router = APIRouter(prefix="/api/v1/subnets", tags=["Public Subnets"])

class SubnetCreate(BaseModel):
    name: str
    cidr: str
    gateway: str

class SubnetResponse(BaseModel):
    id: int
    name: str
    cidr: str
    gateway: str
    router_ip: str
    total_ips: int
    allocated_ips: int
    available_ips: int
    created_at: Optional[str]

class FloatingIPResponse(BaseModel):
    id: int
    ip_address: str
    subnet_id: int
    is_allocated: bool
    vm_name: Optional[str]

# Admin endpoints
@router.post("/", response_model=SubnetResponse)
async def add_public_subnet(
    subnet_data: SubnetCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Add a new public subnet (Admin only)"""
    try:
        service = PublicSubnetService(db)
        result = service.add_public_subnet(
            name=subnet_data.name,
            cidr=subnet_data.cidr,
            gateway=subnet_data.gateway
        )
        
        # Refresh to get full details
        return service.list_public_subnets()[0]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[SubnetResponse])
async def list_public_subnets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all public subnets"""
    service = PublicSubnetService(db)
    return service.list_public_subnets()

@router.delete("/{subnet_id}")
async def remove_public_subnet(
    subnet_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Remove a public subnet (Admin only)"""
    try:
        service = PublicSubnetService(db)
        return service.remove_public_subnet(subnet_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/floating-ips/available", response_model=List[FloatingIPResponse])
async def get_available_floating_ips(
    subnet_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available floating IPs"""
    service = PublicSubnetService(db)
    return service.get_available_floating_ips(subnet_id)

@router.post("/floating-ips/assign")
async def assign_floating_ip(
    vm_name: str,
    subnet_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign a floating IP to a VM"""
    try:
        service = FloatingIPService(db)
        return service.assign_floating_ip(vm_name, subnet_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/floating-ips/release")
async def release_floating_ip(
    ip_address: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Release a floating IP"""
    try:
        service = FloatingIPService(db)
        return service.release_floating_ip(ip_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))