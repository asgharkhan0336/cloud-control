"""Subnets API - Subnet Management within VPCs"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.services.vpc_service import VPCService

router = APIRouter(prefix="/api/v1/subnets", tags=["Subnets"])

# ============================================
# Pydantic Schemas
# ============================================

class SubnetCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    vpc_id: int
    cidr: str = Field(..., pattern="^([0-9]{1,3}\\.){3}[0-9]{1,3}/[0-9]{1,2}$")
    is_public: bool = False

class SubnetResponse(BaseModel):
    id: int
    name: str
    vpc_id: int
    cidr: str
    gateway: str
    is_public: bool
    total_ips: int
    used_ips: int
    available_ips: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================
# Subnet Endpoints
# ============================================

@router.get("/", response_model=List[SubnetResponse])
async def list_subnets(
    vpc_id: Optional[int] = Query(None, description="Filter by VPC ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List subnets (optionally filtered by VPC)"""
    service = VPCService(db)
    
    if vpc_id:
        return service.list_subnets(vpc_id, current_user.id)
    
    return service.list_all_user_subnets(current_user.id)

@router.post("/", response_model=SubnetResponse, status_code=status.HTTP_201_CREATED)
async def create_subnet(
    subnet_data: SubnetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new subnet in a VPC"""
    try:
        service = VPCService(db)
        return service.create_subnet(
            vpc_id=subnet_data.vpc_id,
            user_id=current_user.id,
            name=subnet_data.name,
            cidr=subnet_data.cidr,
            is_public=subnet_data.is_public
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create subnet: {str(e)}")

@router.get("/{subnet_id}", response_model=SubnetResponse)
async def get_subnet(
    subnet_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get subnet details"""
    service = VPCService(db)
    subnet = service.get_subnet(subnet_id, current_user.id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    return subnet

@router.delete("/{subnet_id}")
async def delete_subnet(
    subnet_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a subnet"""
    try:
        service = VPCService(db)
        return service.delete_subnet(subnet_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete subnet: {str(e)}")

@router.get("/{subnet_id}/available-ips")
async def get_available_ips(
    subnet_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available IP addresses in a subnet"""
    service = VPCService(db)
    return service.get_available_ips(subnet_id, current_user.id)