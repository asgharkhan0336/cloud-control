"""VPC API - Virtual Private Cloud Management"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.services.vpc_service import VPCService

router = APIRouter(prefix="/api/v1/vpc", tags=["VPC"])

# ============================================
# Pydantic Schemas
# ============================================

class VPCCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    description: Optional[str] = Field(None, max_length=255)
    cidr: Optional[str] = Field(None, pattern="^([0-9]{1,3}\\.){3}[0-9]{1,3}/[0-9]{1,2}$")

class VPCResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    cidr: str
    gateway: str
    vni: int
    is_default: bool
    created_at: datetime
    vm_count: int
    subnet_count: int
    
    class Config:
        from_attributes = True

class VPCPeeringCreate(BaseModel):
    peer_vpc_id: int

class VPCPeeringResponse(BaseModel):
    id: int
    vpc_a_id: int
    vpc_b_id: int
    status: str
    created_at: datetime
    accepted_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ============================================
# VPC Endpoints
# ============================================

@router.get("/", response_model=List[VPCResponse])
async def list_vpcs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all VPCs for the current user"""
    service = VPCService(db)
    return service.list_user_vpcs(current_user.id)

@router.post("/", response_model=VPCResponse, status_code=status.HTTP_201_CREATED)
async def create_vpc(
    vpc_data: VPCCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new VPC"""
    try:
        service = VPCService(db)
        return service.create_vpc(
            user_id=current_user.id,
            name=vpc_data.name,
            description=vpc_data.description,
            cidr=vpc_data.cidr
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create VPC: {str(e)}")

@router.get("/{vpc_id}", response_model=VPCResponse)
async def get_vpc(
    vpc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get VPC details"""
    service = VPCService(db)
    vpc = service.get_vpc(vpc_id, current_user.id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")
    return vpc

@router.delete("/{vpc_id}")
async def delete_vpc(
    vpc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a VPC"""
    try:
        service = VPCService(db)
        return service.delete_vpc(vpc_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete VPC: {str(e)}")

@router.post("/{vpc_id}/peer", response_model=VPCPeeringResponse)
async def create_vpc_peering(
    vpc_id: int,
    peering_data: VPCPeeringCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create VPC peering request"""
    try:
        service = VPCService(db)
        return service.create_peering(vpc_id, peering_data.peer_vpc_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create peering: {str(e)}")

@router.post("/peer/{peering_id}/accept")
async def accept_vpc_peering(
    peering_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Accept VPC peering request"""
    try:
        service = VPCService(db)
        return service.accept_peering(peering_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to accept peering: {str(e)}")

@router.get("/{vpc_id}/peerings", response_model=List[VPCPeeringResponse])
async def list_vpc_peerings(
    vpc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all peerings for a VPC"""
    service = VPCService(db)
    return service.list_peerings(vpc_id, current_user.id)