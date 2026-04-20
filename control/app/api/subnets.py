from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User, Subnet
from app.services.vpc_service import VPCService

router = APIRouter(prefix="/api/v1/subnets", tags=["Subnets"])

class SubnetCreate(BaseModel):
    name: str
    cidr: str
    vpc_id: int
    is_public: bool = False

class SubnetResponse(BaseModel):
    id: int
    name: str
    vpc_id: int
    cidr: str
    gateway: str
    is_public: bool
    created_at: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[SubnetResponse])
async def list_subnets(
    vpc_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List subnets (optionally filtered by VPC)"""
    if vpc_id:
        service = VPCService(db)
        return service.list_subnets(vpc_id, current_user.id)
    
    # If no vpc_id, return all user's subnets
    from app.models.database import Network
    subnets = db.query(Subnet).join(Network).filter(
        Network.owner_id == current_user.id
    ).all()
    return subnets

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

@router.get("/{subnet_id}", response_model=SubnetResponse)
async def get_subnet(
    subnet_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get subnet details"""
    from app.models.database import Network
    subnet = db.query(Subnet).join(Network).filter(
        Subnet.id == subnet_id,
        Network.owner_id == current_user.id
    ).first()
    
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