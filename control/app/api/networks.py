from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import ipaddress

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User, Network
from app.services.ovn_service import OVNService

router = APIRouter(prefix="/api/v1/networks", tags=["Networks"])
ovn_service = OVNService()

class NetworkCreate(BaseModel):
    name: str
    cidr: str
    vlan_id: Optional[int] = None
    is_public: bool = False

class NetworkResponse(BaseModel):
    id: int
    name: str
    cidr: str
    gateway: str
    vlan_id: Optional[int]
    is_public: bool
    
    class Config:
        from_attributes = True

class FloatingIPCreate(BaseModel):
    network_id: int
    vm_name: Optional[str] = None

class FloatingIPResponse(BaseModel):
    id: int
    ip_address: str
    vm_name: Optional[str]
    is_allocated: bool
    
    class Config:
        from_attributes = True

@router.post("/", response_model=NetworkResponse)
async def create_network(
    network_data: NetworkCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new private network"""
    try:
        # Validate CIDR
        network = ipaddress.ip_network(network_data.cidr, strict=False)
        gateway = str(list(network.hosts())[0])
        
        # Check if network name exists
        existing = db.query(Network).filter(Network.name == network_data.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Network name already exists"
            )
        
        # Create OVN logical switch
        ovn_service.create_logical_switch(network_data.name, network_data.cidr)
        
        # Save to database
        db_network = Network(
            name=network_data.name,
            owner_id=current_user.id,
            cidr=network_data.cidr,
            gateway=gateway,
            vlan_id=network_data.vlan_id,
            is_public=network_data.is_public
        )
        
        db.add(db_network)
        db.commit()
        db.refresh(db_network)
        
        return db_network
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[NetworkResponse])
async def list_networks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all networks for current user"""
    if current_user.is_superuser:
        networks = db.query(Network).all()
    else:
        networks = db.query(Network).filter(Network.owner_id == current_user.id).all()
    return networks

@router.get("/{network_id}", response_model=NetworkResponse)
async def get_network(
    network_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get network details"""
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    if not current_user.is_superuser and network.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return network

@router.delete("/{network_id}")
async def delete_network(
    network_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a network"""
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    if not current_user.is_superuser and network.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        # Delete OVN logical switch
        ovn_service.delete_logical_switch(network.name)
        
        # Delete from database
        db.delete(network)
        db.commit()
        
        return {"message": "Network deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{network_id}/connect/{vm_name}")
async def connect_vm_to_network(
    network_id: int,
    vm_name: str,
    ip_address: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Connect a VM to a network"""
    # Verify network access
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    if not current_user.is_superuser and network.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        # Create OVN port
        port_info = ovn_service.create_vm_port(
            network.name, vm_name, ip_address=ip_address
        )
        
        # Update VM in database
        from app.models.database import VM
        vm = db.query(VM).filter(VM.name == vm_name).first()
        if vm:
            vm.private_ip = ip_address
            vm.network_name = network.name
            db.commit()
        
        return {
            "message": f"VM {vm_name} connected to network {network.name}",
            "port_info": port_info
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
