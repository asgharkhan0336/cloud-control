"""VM Service - Tenant-based VM Management"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.libvirt_service import LibvirtService
from app.models.vm import VMResponse, VMListResponse
from app.models.database import VM, Network, Subnet, SecurityGroup

class VMService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_vms(self, user_id: int, is_superuser: bool = False) -> VMListResponse:
        """List all VMs for current user"""
        with LibvirtService() as libvirt:
            # Get all VMs from libvirt
            libvirt_vms = libvirt.list_vms()
            
            # Get user's VMs from database
            if is_superuser:
                db_vms = self.db.query(VM).all()
            else:
                db_vms = self.db.query(VM).filter(VM.owner_id == user_id).all()
            
            # Create mapping of VM name to database VM
            db_vm_map = {vm.name: vm for vm in db_vms}
            
            # Filter and merge VMs
            user_vms = []
            for libvirt_vm in libvirt_vms:
                vm_name = libvirt_vm['name']
                db_vm = db_vm_map.get(vm_name)
                
                # Only include VMs that belong to the user (or all if superuser)
                if db_vm or is_superuser:
                    vm_data = self._merge_vm_data(libvirt_vm, db_vm)
                    user_vms.append(vm_data)
            
            running = sum(1 for vm in user_vms if vm.get('state') == 'running')
            
            return VMListResponse(
                vms=[VMResponse(**vm) for vm in user_vms],
                total=len(user_vms),
                running=running,
                stopped=len(user_vms) - running
            )
    
    def get_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> Optional[Dict[str, Any]]:
        """Get specific VM by ID (tenant-based)"""
        # Query database first
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            return None
        
        # Get VM info from libvirt
        with LibvirtService() as libvirt:
            libvirt_vm = libvirt.get_vm(db_vm.name)
            if not libvirt_vm:
                # VM exists in DB but not in libvirt (orphaned record)
                return self._merge_vm_data({
                    'name': db_vm.name,
                    'state': 'unknown',
                    'memory': db_vm.memory,
                    'vcpus': db_vm.vcpus,
                    'cpu_time': 0,
                    'cpu_percent': 0.0,
                    'ip_addresses': [],
                    'disk_usage': {}
                }, db_vm)
            
            return self._merge_vm_data(libvirt_vm, db_vm)
    
    def get_vm_by_name(self, name: str, user_id: int, is_superuser: bool = False) -> Optional[Dict[str, Any]]:
        """Get VM by name (tenant-based)"""
        query = self.db.query(VM).filter(VM.name == name)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            return None
        
        with LibvirtService() as libvirt:
            libvirt_vm = libvirt.get_vm(name)
            if not libvirt_vm:
                return self._merge_vm_data({
                    'name': name,
                    'state': 'unknown',
                    'memory': db_vm.memory,
                    'vcpus': db_vm.vcpus,
                    'cpu_time': 0,
                    'cpu_percent': 0.0,
                    'ip_addresses': [],
                    'disk_usage': {}
                }, db_vm)
            
            return self._merge_vm_data(libvirt_vm, db_vm)
    
def create_vm(self, user_id: int, **kwargs) -> Dict[str, Any]:
    """Create a new VM for a user"""
    vm_name = kwargs.get('name')
    if not vm_name:
        raise ValueError("VM name is required")
    
    # Check if VM already exists in database
    existing = self.db.query(VM).filter(VM.name == vm_name).first()
    if existing:
        raise ValueError(f"VM with name '{vm_name}' already exists")
    
    # Separate libvirt params from database params
    libvirt_params = {
        'name': vm_name,
        'memory': kwargs.get('memory', 1024),
        'vcpus': kwargs.get('vcpus', 1),
        'disk_size': kwargs.get('disk_size', 10),
        'os_variant': kwargs.get('os_variant', 'ubuntu24.04'),
        'network_bridge': kwargs.get('network_bridge', 'virbr0')
    }
    
    # Add optional libvirt params if present
    if kwargs.get('ssh_key'):
        libvirt_params['ssh_key'] = kwargs['ssh_key']
    if kwargs.get('user_data'):
        libvirt_params['user_data'] = kwargs['user_data']
    
    # Create VM in libvirt
    with LibvirtService() as libvirt:
        success = libvirt.create_vm(**libvirt_params)
        if not success:
            raise Exception("Failed to create VM in libvirt")
    
    # Save to database with additional fields
    db_vm = VM(
        name=vm_name,
        owner_id=user_id,
        memory=libvirt_params['memory'],
        vcpus=libvirt_params['vcpus'],
        disk_size=libvirt_params['disk_size'],
        os_variant=libvirt_params['os_variant'],
        status='stopped',
        vpc_id=kwargs.get('vpc_id'),
        subnet_id=kwargs.get('subnet_id'),
        private_ip=kwargs.get('private_ip'),
        network_name=libvirt_params['network_bridge']
    )
    self.db.add(db_vm)
    self.db.commit()
    self.db.refresh(db_vm)
    
    # Assign security groups if provided
    if kwargs.get('security_group_ids'):
        from app.models.database import SecurityGroup, VMSecurityGroup
        for sg_id in kwargs['security_group_ids']:
            sg = self.db.query(SecurityGroup).filter(
                SecurityGroup.id == sg_id,
                SecurityGroup.owner_id == user_id
            ).first()
            if sg:
                vm_sg = VMSecurityGroup(vm_id=db_vm.id, security_group_id=sg_id)
                self.db.add(vm_sg)
        self.db.commit()
    
    # If VPC and subnet are provided, allocate private IP
    if kwargs.get('vpc_id') and kwargs.get('subnet_id') and not kwargs.get('private_ip'):
        from app.services.vpc_service import VPCService
        vpc_service = VPCService(self.db)
        available_ips = vpc_service.get_available_ips(kwargs['subnet_id'], user_id)
        if available_ips and available_ips.get('available_list'):
            db_vm.private_ip = available_ips['available_list'][0]
            self.db.commit()
    
    return self._merge_vm_data({
        'name': vm_name,
        'state': 'stopped',
        'memory': db_vm.memory,
        'vcpus': db_vm.vcpus,
        'cpu_time': 0,
        'cpu_percent': 0.0,
        'ip_addresses': [db_vm.private_ip] if db_vm.private_ip else [],
        'disk_usage': {}
    }, db_vm)

    
def start_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
    """Start a VM (tenant-based)"""
    # Verify ownership
    query = self.db.query(VM).filter(VM.id == vm_id)
    if not is_superuser:
        query = query.filter(VM.owner_id == user_id)
    
    db_vm = query.first()
    if not db_vm:
        raise ValueError("VM not found")
    
    # Start in libvirt
    with LibvirtService() as libvirt:
        success = libvirt.start_vm(db_vm.name)
        if success:
            db_vm.status = 'running'
            self.db.commit()
        return success
    
def stop_vm(self, vm_id: int, user_id: int, force: bool = False, is_superuser: bool = False) -> bool:
    """Stop a VM (tenant-based)"""
    # Verify ownership
    query = self.db.query(VM).filter(VM.id == vm_id)
    if not is_superuser:
        query = query.filter(VM.owner_id == user_id)
    
    db_vm = query.first()
    if not db_vm:
        raise ValueError("VM not found")
    
    # Stop in libvirt
    with LibvirtService() as libvirt:
        success = libvirt.stop_vm(db_vm.name, force)
        if success:
            db_vm.status = 'stopped'
            self.db.commit()
        return success
    
    def reboot_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Reboot a VM (tenant-based)"""
        # Verify ownership
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            raise ValueError("VM not found")
        
        # Reboot in libvirt
        with LibvirtService() as libvirt:
            return libvirt.reboot_vm(db_vm.name)
    
    def pause_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Pause a VM (tenant-based)"""
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.pause_vm(db_vm.name)
            if success:
                db_vm.status = 'paused'
                self.db.commit()
            return success
    
    def resume_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Resume a paused VM (tenant-based)"""
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.resume_vm(db_vm.name)
            if success:
                db_vm.status = 'running'
                self.db.commit()
            return success
    
    def delete_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Delete a VM (tenant-based)"""
        # Verify ownership
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            raise ValueError("VM not found")
        
        vm_name = db_vm.name
        
        # Delete from libvirt
        with LibvirtService() as libvirt:
            try:
                libvirt.delete_vm(vm_name)
            except Exception as e:
                print(f"Warning: Failed to delete VM from libvirt: {e}")
        
        # Delete security group associations
        from app.models.database import VMSecurityGroup
        self.db.query(VMSecurityGroup).filter(VMSecurityGroup.vm_id == vm_id).delete()
        
        # Delete from database
        self.db.delete(db_vm)
        self.db.commit()
        
        return True
    
    def assign_floating_ip(self, vm_id: int, floating_ip: str, user_id: int, is_superuser: bool = False) -> bool:
        """Assign floating IP to VM"""
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            raise ValueError("VM not found")
        
        db_vm.floating_ip = floating_ip
        self.db.commit()
        return True
    
    def _merge_vm_data(self, libvirt_vm: Dict[str, Any], db_vm: Optional[VM]) -> Dict[str, Any]:
        """Merge libvirt VM data with database VM data"""
        vm_data = dict(libvirt_vm)
        
        if db_vm:
            vm_data['id'] = db_vm.id
            vm_data['owner_id'] = db_vm.owner_id
            vm_data['vpc_id'] = db_vm.vpc_id
            vm_data['subnet_id'] = db_vm.subnet_id
            vm_data['private_ip'] = db_vm.private_ip
            vm_data['floating_ip'] = db_vm.floating_ip
            vm_data['disk_size'] = db_vm.disk_size
            vm_data['os_variant'] = db_vm.os_variant
            vm_data['created_at'] = db_vm.created_at.isoformat() if db_vm.created_at else None
            
            # Get VPC name
            if db_vm.vpc_id:
                vpc = self.db.query(Network).filter(Network.id == db_vm.vpc_id).first()
                if vpc:
                    vm_data['vpc_name'] = vpc.name
                    vm_data['vpc_cidr'] = vpc.cidr
            
            # Get subnet name
            if db_vm.subnet_id:
                subnet = self.db.query(Subnet).filter(Subnet.id == db_vm.subnet_id).first()
                if subnet:
                    vm_data['subnet_name'] = subnet.name
                    vm_data['subnet_cidr'] = subnet.cidr
            
            # Get security groups
            security_groups = []
            if hasattr(db_vm, 'security_groups') and db_vm.security_groups:
                for sg in db_vm.security_groups:
                    security_groups.append({
                        'id': sg.id,
                        'name': sg.name,
                        'description': sg.description
                    })
            vm_data['security_groups'] = security_groups
        else:
            vm_data['id'] = None
            vm_data['owner_id'] = None
            vm_data['vpc_id'] = None
            vm_data['vpc_name'] = None
            vm_data['subnet_id'] = None
            vm_data['subnet_name'] = None
            vm_data['private_ip'] = None
            vm_data['floating_ip'] = None
            vm_data['created_at'] = None
            vm_data['security_groups'] = []
        
        return vm_data