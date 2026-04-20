"""VPC API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.services.vpc_service import VPCService

router = APIRouter(prefix="/api/v1/vpc", tags=["VPC"])

# ============================================
# Pydantic Models
# ============================================

class VPCCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    description: Optional[str] = Field(None, max_length=255)
    subnet_cidr: Optional[str] = None

class VPCResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    cidr: str
    gateway: str
    vni: int
    is_default: bool
    created_at: Optional[str]
    vm_count: int
    subnet_count: int

class SubnetCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    cidr: str
    is_public: bool = False

class SubnetResponse(BaseModel):
    id: int
    name: str
    cidr: str
    gateway: str
    is_public: bool
    total_ips: int
    used_ips: int
    available_ips: int
    created_at: Optional[str]

class VPCPeeringCreate(BaseModel):
    peer_vpc_id: int

class VPCPeeringResponse(BaseModel):
    id: int
    vpc_a_id: int
    vpc_b_id: int
    status: str
    created_at: Optional[str]
    accepted_at: Optional[str]

# ============================================
# VPC Endpoints
# ============================================

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
            subnet_cidr=vpc_data.subnet_cidr
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[VPCResponse])
async def list_vpcs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all VPCs"""
    service = VPCService(db)
    return service.list_user_vpcs(current_user.id)

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

# ============================================
# Subnet Endpoints
# ============================================

@router.post("/{vpc_id}/subnets", response_model=SubnetResponse)
async def create_subnet(
    vpc_id: int,
    subnet_data: SubnetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a subnet in a VPC"""
    try:
        service = VPCService(db)
        return service.create_subnet(
            vpc_id=vpc_id,
            user_id=current_user.id,
            name=subnet_data.name,
            cidr=subnet_data.cidr,
            is_public=subnet_data.is_public
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{vpc_id}/subnets", response_model=List[SubnetResponse])
async def list_subnets(
    vpc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List subnets in a VPC"""
    try:
        service = VPCService(db)
        return service.list_subnets(vpc_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/subnets/{subnet_id}")
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

# ============================================
# VPC Peering Endpoints
# ============================================

@router.post("/{vpc_id}/peer", response_model=VPCPeeringResponse)
async def create_peering(
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

@router.post("/peer/{peering_id}/accept")
async def accept_peering(
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