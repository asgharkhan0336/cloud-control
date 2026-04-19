from typing import List, Dict, Any, Optional
from app.services.libvirt_service import LibvirtService
from app.models.vm import VMResponse, VMListResponse

class VMService:
    def list_vms(self) -> VMListResponse:
        """List all VMs with statistics"""
        with LibvirtService() as libvirt:
            vms = libvirt.list_vms()
            vm_responses = [VMResponse(**vm) for vm in vms]
            running = sum(1 for vm in vms if vm['state'] == 'running')
            
            return VMListResponse(
                vms=vm_responses,
                total=len(vm_responses),
                running=running,
                stopped=len(vm_responses) - running
            )
    
    def get_vm(self, name: str) -> Optional[VMResponse]:
        """Get specific VM information"""
        with LibvirtService() as libvirt:
            vm_info = libvirt.get_vm(name)
            if vm_info:
                return VMResponse(**vm_info)
        return None
    
    def create_vm(self, **kwargs) -> bool:
        """Create a new VM"""
        with LibvirtService() as libvirt:
            return libvirt.create_vm(**kwargs)
    
    def start_vm(self, name: str) -> bool:
        """Start a VM"""
        with LibvirtService() as libvirt:
            return libvirt.start_vm(name)
    
    def stop_vm(self, name: str, force: bool = False) -> bool:
        """Stop a VM"""
        with LibvirtService() as libvirt:
            return libvirt.stop_vm(name, force)
    
    def delete_vm(self, name: str) -> bool:
        """Delete a VM"""
        with LibvirtService() as libvirt:
            return libvirt.delete_vm(name)
