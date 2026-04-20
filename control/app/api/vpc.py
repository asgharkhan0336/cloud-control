"""Tenant VPC Management - Users manage their own private networks"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User, Network, VM
from app.services.vpc_service import VPCService
from app.services.firewall_service import FirewallService

router = APIRouter(prefix="/api/v1/vpc", tags=["VPC"])

# ============================================
# Pydantic Models
# ============================================

class VPCCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    description: Optional[str] = None
    subnet_cidr: Optional[str] = None  # Auto-assigned if not provided

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
    
    class Config:
        from_attributes = True

class SubnetCreate(BaseModel):
    name: str
    cidr: str
    
class SubnetResponse(BaseModel):
    id: int
    name: str
    cidr: str
    gateway: str
    available_ips: int
    is_public: bool

class VPCPeeringCreate(BaseModel):
    peer_vpc_id: int
    peer_account_id: Optional[str] = None  # For cross-account peering

class VPCPeeringResponse(BaseModel):
    id: int
    vpc_id: int
    peer_vpc_id: int
    status: str
    created_at: datetime

# ============================================
# VPC Endpoints
# ============================================

@router.post("/", response_model=VPCResponse)
async def create_vpc(
    vpc_data: VPCCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new VPC (Virtual Private Cloud)
    Users can create multiple VPCs for isolation
    """
    try:
        service = VPCService(db)
        vpc = service.create_vpc(
            user_id=current_user.id,
            name=vpc_data.name,
            description=vpc_data.description,
            subnet_cidr=vpc_data.subnet_cidr
        )
        return vpc
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list", response_model=List[VPCResponse])
async def list_vpcs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all VPCs for the current user"""
    service = VPCService(db)
    return service.list_user_vpcs(current_user.id)

@router.get("/{vpc_id}", response_model=VPCResponse)
async def get_vpc(
    vpc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific VPC"""
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
    """
    Delete a VPC
    Cannot delete if it contains VMs or has active peerings
    """
    try:
        service = VPCService(db)
        result = service.delete_vpc(vpc_id, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Subnet Endpoints (within VPC)
# ============================================

@router.post("/{vpc_id}/subnets", response_model=SubnetResponse)
async def create_subnet(
    vpc_id: int,
    subnet_data: SubnetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a subnet within a VPC
    Users can segment their VPC into multiple subnets
    """
    try:
        service = VPCService(db)
        subnet = service.create_subnet(
            vpc_id=vpc_id,
            user_id=current_user.id,
            name=subnet_data.name,
            cidr=subnet_data.cidr
        )
        return subnet
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{vpc_id}/subnets", response_model=List[SubnetResponse])
async def list_subnets(
    vpc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all subnets in a VPC"""
    service = VPCService(db)
    return service.list_subnets(vpc_id, current_user.id)

# ============================================
# VPC Peering Endpoints
# ============================================

@router.post("/{vpc_id}/peer", response_model=VPCPeeringResponse)
async def create_vpc_peering(
    vpc_id: int,
    peering_data: VPCPeeringCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create VPC peering connection
    Connect two VPCs (same account or cross-account)
    """
    try:
        service = VPCService(db)
        peering = service.create_peering(
            vpc_id=vpc_id,
            peer_vpc_id=peering_data.peer_vpc_id,
            user_id=current_user.id
        )
        return peering
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/peer/{peering_id}/accept")
async def accept_vpc_peering(
    peering_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Accept a VPC peering request"""
    try:
        service = VPCService(db)
        return service.accept_peering(peering_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))