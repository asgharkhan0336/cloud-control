"""VM API Endpoints - Tenant-based"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.models.vm import VMCreateRequest, VMResponse, VMListResponse, APIResponse
from app.services.vm_service import VMService
from app.services.console_service import ConsoleService

router = APIRouter(prefix="/api/v1/vms", tags=["VMs"])

@router.get("/", response_model=VMListResponse)
async def list_vms(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all VMs for current user"""
    try:
        service = VMService(db)
        return service.list_vms(current_user.id, current_user.is_superuser)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vm_id}", response_model=VMResponse)
async def get_vm(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get VM by ID"""
    service = VMService(db)
    vm = service.get_vm(vm_id, current_user.id, current_user.is_superuser)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return VMResponse(**vm)

@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_vm(
    vm_request: VMCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new VM"""
    try:
        service = VMService(db)
        
        # Build kwargs for service
        kwargs = {
            'name': vm_request.name,
            'memory': vm_request.memory,
            'vcpus': vm_request.vcpus,
            'disk_size': vm_request.disk_size,
            'os_variant': vm_request.os_variant,
            'network_bridge': vm_request.network_bridge,
            'vpc_id': vm_request.vpc_id,
            'subnet_id': vm_request.subnet_id,
            'private_ip': vm_request.private_ip,
            'security_group_ids': vm_request.security_group_ids,
            'ssh_key': vm_request.ssh_key,
            'user_data': vm_request.user_data,
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        vm = service.create_vm(user_id=current_user.id, **kwargs)
        return APIResponse(success=True, message="VM created successfully", data=vm)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{vm_id}/start", response_model=APIResponse)
async def start_vm(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a VM"""
    try:
        service = VMService(db)
        service.start_vm(vm_id, current_user.id, current_user.is_superuser)
        return APIResponse(success=True, message="VM started")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{vm_id}/stop", response_model=APIResponse)
async def stop_vm(
    vm_id: int,
    force: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Stop a VM"""
    try:
        service = VMService(db)
        service.stop_vm(vm_id, current_user.id, force, current_user.is_superuser)
        return APIResponse(success=True, message="VM stopped")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{vm_id}/reboot", response_model=APIResponse)
async def reboot_vm(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reboot a VM"""
    try:
        service = VMService(db)
        service.reboot_vm(vm_id, current_user.id, current_user.is_superuser)
        return APIResponse(success=True, message="VM rebooted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{vm_id}/pause", response_model=APIResponse)
async def pause_vm(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Pause a VM"""
    try:
        service = VMService(db)
        service.pause_vm(vm_id, current_user.id, current_user.is_superuser)
        return APIResponse(success=True, message="VM paused")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{vm_id}/resume", response_model=APIResponse)
async def resume_vm(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Resume a paused VM"""
    try:
        service = VMService(db)
        service.resume_vm(vm_id, current_user.id, current_user.is_superuser)
        return APIResponse(success=True, message="VM resumed")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{vm_id}", response_model=APIResponse)
async def delete_vm(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a VM"""
    try:
        service = VMService(db)
        service.delete_vm(vm_id, current_user.id, current_user.is_superuser)
        return APIResponse(success=True, message="VM deleted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{vm_id}/console")
async def request_console(
    vm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Request console access - returns one-time URL"""
    service = ConsoleService(db)
    session = service.create_console_session(vm_id, current_user.id)
    
    return {
        'url': session['url'],
        'expires_in': session['expires_in']
    }