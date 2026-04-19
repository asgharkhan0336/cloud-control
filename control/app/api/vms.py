from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.vm_service import VMService
from app.models.vm import (
    VMCreateRequest, VMResponse, VMListResponse,
    HostInfoResponse, APIResponse
)
from app.services.libvirt_service import LibvirtService
from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User, VM, ResourceQuota

router = APIRouter(prefix="/api/v1", tags=["VMs"])
vm_service = VMService()

def check_vm_quota(db: Session, user: User, memory: int, vcpus: int, disk_size: int):
    """Check if user has enough quota to create VM"""
    quota = db.query(ResourceQuota).filter(ResourceQuota.user_id == user.id).first()
    if not quota:
        quota = ResourceQuota(user_id=user.id)
        db.add(quota)
        db.commit()
        db.refresh(quota)
    
    # Count existing VMs
    vm_count = db.query(VM).filter(VM.owner_id == user.id).count()
    if vm_count >= quota.max_vms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"VM quota exceeded. Maximum {quota.max_vms} VMs allowed."
        )
    
    # Check resource quotas
    total_memory = db.query(func.sum(VM.memory)).filter(VM.owner_id == user.id).scalar() or 0
    if total_memory + memory > quota.max_memory_mb:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Memory quota exceeded. Maximum {quota.max_memory_mb} MB allowed."
        )
    
    total_vcpus = db.query(func.sum(VM.vcpus)).filter(VM.owner_id == user.id).scalar() or 0
    if total_vcpus + vcpus > quota.max_vcpus:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"vCPU quota exceeded. Maximum {quota.max_vcpus} vCPUs allowed."
        )
    
    total_disk = db.query(func.sum(VM.disk_size)).filter(VM.owner_id == user.id).scalar() or 0
    if total_disk + disk_size > quota.max_disk_gb:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Disk quota exceeded. Maximum {quota.max_disk_gb} GB allowed."
        )

@router.get("/vms", response_model=VMListResponse)
async def list_vms(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all virtual machines for current user"""
    try:
        # Get VMs from libvirt
        all_vms = vm_service.list_vms()
        
        # Filter VMs owned by current user (unless superuser)
        if current_user.is_superuser:
            user_vms = all_vms.vms
        else:
            db_vm_names = [vm.name for vm in db.query(VM).filter(VM.owner_id == current_user.id).all()]
            user_vms = [vm for vm in all_vms.vms if vm.name in db_vm_names]
        
        running = sum(1 for vm in user_vms if vm.state == 'running')
        
        return VMListResponse(
            vms=user_vms,
            total=len(user_vms),
            running=running,
            stopped=len(user_vms) - running
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list VMs: {str(e)}"
        )

@router.post("/vms", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_vm(
    vm_request: VMCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new virtual machine"""
    try:
        # Check quota
        check_vm_quota(db, current_user, vm_request.memory, vm_request.vcpus, vm_request.disk_size)
        
        # Check if VM name already exists
        existing_vm = db.query(VM).filter(VM.name == vm_request.name).first()
        if existing_vm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"VM '{vm_request.name}' already exists"
            )
        
        # Create VM in libvirt
        success = vm_service.create_vm(
            name=vm_request.name,
            memory=vm_request.memory,
            vcpus=vm_request.vcpus,
            disk_size=vm_request.disk_size,
            os_variant=vm_request.os_variant,
            network_bridge=vm_request.network_bridge
        )
        
        if success:
            # Save VM in database
            db_vm = VM(
                name=vm_request.name,
                owner_id=current_user.id,
                memory=vm_request.memory,
                vcpus=vm_request.vcpus,
                disk_size=vm_request.disk_size,
                os_variant=vm_request.os_variant,
                status="stopped",
                network_name=vm_request.network_bridge
            )
            db.add(db_vm)
            db.commit()
            
            return APIResponse(
                success=True,
                message=f"VM '{vm_request.name}' created successfully",
                data={"name": vm_request.name}
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create VM: {str(e)}"
        )

@router.get("/vms/{name}", response_model=VMResponse)
async def get_vm(
    name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific VM"""
    db_vm = db.query(VM).filter(VM.name == name).first()
    if not db_vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' not found")
    
    if not current_user.is_superuser and db_vm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vm = vm_service.get_vm(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' not found")
    return vm

@router.post("/vms/{name}/start", response_model=APIResponse)
async def start_vm(
    name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a virtual machine"""
    db_vm = db.query(VM).filter(VM.name == name).first()
    if not db_vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' not found")
    
    if not current_user.is_superuser and db_vm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        success = vm_service.start_vm(name)
        if success:
            db_vm.status = "running"
            db.commit()
            return APIResponse(success=True, message=f"VM '{name}' started")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start VM: {str(e)}")

@router.post("/vms/{name}/stop", response_model=APIResponse)
async def stop_vm(
    name: str,
    force: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Stop a virtual machine"""
    db_vm = db.query(VM).filter(VM.name == name).first()
    if not db_vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' not found")
    
    if not current_user.is_superuser and db_vm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        success = vm_service.stop_vm(name, force)
        if success:
            db_vm.status = "stopped"
            db.commit()
            return APIResponse(success=True, message=f"VM '{name}' stopped")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to stop VM: {str(e)}")

@router.delete("/vms/{name}", response_model=APIResponse)
async def delete_vm(
    name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a virtual machine"""
    db_vm = db.query(VM).filter(VM.name == name).first()
    if not db_vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' not found")
    
    if not current_user.is_superuser and db_vm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        success = vm_service.delete_vm(name)
        if success:
            db.delete(db_vm)
            db.commit()
            return APIResponse(success=True, message=f"VM '{name}' deleted")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete VM: {str(e)}")
