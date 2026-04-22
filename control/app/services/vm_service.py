"""VM Service - Complete Tenant-based VM Management"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.libvirt_service import LibvirtService
from app.services.ovn_service import OVNService
from app.models.vm import VMResponse, VMListResponse
from app.models.database import VM, Network, Subnet, SecurityGroup, VMSecurityGroup

class VMService:
    def __init__(self, db: Session):
        self.db = db
        self.ovn = OVNService()
    
    # ============================================
    # VM Listing and Retrieval
    # ============================================
    
    def list_vms(self, user_id: int, is_superuser: bool = False) -> VMListResponse:
        """List all VMs for current user"""
        with LibvirtService() as libvirt:
            libvirt_vms = libvirt.list_vms()
            
            if is_superuser:
                db_vms = self.db.query(VM).all()
            else:
                db_vms = self.db.query(VM).filter(VM.owner_id == user_id).all()
            
            db_vm_map = {vm.name: vm for vm in db_vms}
            
            user_vms = []
            for libvirt_vm in libvirt_vms:
                vm_name = libvirt_vm['name']
                db_vm = db_vm_map.get(vm_name)
                
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
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        
        db_vm = query.first()
        if not db_vm:
            return None
        
        with LibvirtService() as libvirt:
            libvirt_vm = libvirt.get_vm(db_vm.name)
            if not libvirt_vm:
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
    
    # ============================================
    # VM Creation
    # ============================================
    
    def create_vm(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Create a new VM with network and security group attachment"""
        vm_name = kwargs.get('name')
        if not vm_name:
            raise ValueError("VM name is required")
        
        # Check if VM already exists in database
        existing = self.db.query(VM).filter(VM.name == vm_name).first()
        if existing:
            raise ValueError(f"VM with name '{vm_name}' already exists")
        
        # Verify VPC and subnet ownership if provided
        vpc_id = kwargs.get('vpc_id')
        subnet_id = kwargs.get('subnet_id')
        vpc = None
        subnet = None
        private_ip = kwargs.get('private_ip')
        
        if vpc_id:
            vpc = self.db.query(Network).filter(
                Network.id == vpc_id,
                Network.owner_id == user_id
            ).first()
            if not vpc:
                raise ValueError("VPC not found or access denied")
        
        if subnet_id:
            subnet = self.db.query(Subnet).filter(
                Subnet.id == subnet_id,
                Subnet.vpc_id == vpc_id
            ).first()
            if not subnet:
                raise ValueError("Subnet not found or not in selected VPC")
            
            # Allocate private IP if subnet is selected but no IP provided
            if not private_ip:
                private_ip = self._allocate_ip_from_subnet(subnet_id, user_id)
        
        # Prepare libvirt parameters
        libvirt_params = {
            'name': vm_name,
            'memory': kwargs.get('memory', 2048),
            'vcpus': kwargs.get('vcpus', 2),
            'disk_size': kwargs.get('disk_size', 20),
            'os_variant': kwargs.get('os_variant', 'ubuntu24.04'),
            'network_bridge': kwargs.get('network_bridge', 'virbr0')  # Default to virbr0
        }
        
        if kwargs.get('ssh_key'):
            libvirt_params['ssh_key'] = kwargs['ssh_key']
        if kwargs.get('user_data'):
            libvirt_params['user_data'] = kwargs['user_data']
        
        # Create VM in libvirt
        with LibvirtService() as libvirt:
            success = libvirt.create_vm(**libvirt_params)
            if not success:
                raise Exception("Failed to create VM in libvirt")
        
        # Save VM to database
        db_vm = VM(
            name=vm_name,
            owner_id=user_id,
            memory=libvirt_params['memory'],
            vcpus=libvirt_params['vcpus'],
            disk_size=libvirt_params['disk_size'],
            os_variant=libvirt_params['os_variant'],
            status='stopped',
            vpc_id=vpc_id,
            subnet_id=subnet_id,
            private_ip=private_ip,
            network_name=libvirt_params['network_bridge']
        )
        self.db.add(db_vm)
        self.db.commit()
        self.db.refresh(db_vm)
        
        # Create OVN port if VPC is selected (only if not using default virbr0)
        if vpc and subnet and private_ip and libvirt_params['network_bridge'] != 'virbr0':
            try:
                tenant_name = self._get_tenant_name(user_id)
                self.ovn.create_vm_port(
                    tenant_name=tenant_name,
                    vm_name=vm_name,
                    private_ip=private_ip
                )
            except Exception as e:
                print(f"Warning: Failed to create OVN port: {e}")
                # Don't fail VM creation if OVN port fails
        
        # Attach security groups
        security_group_ids = kwargs.get('security_group_ids', [])
        if security_group_ids:
            self._attach_security_groups(db_vm.id, security_group_ids, user_id)
        
        return self._merge_vm_data({
            'name': vm_name,
            'state': 'stopped',
            'memory': db_vm.memory,
            'vcpus': db_vm.vcpus,
            'cpu_time': 0,
            'cpu_percent': 0.0,
            'ip_addresses': [private_ip] if private_ip else [],
            'disk_usage': {}
        }, db_vm)
    
    # ============================================
    # VM Power Operations
    # ============================================
    
    def start_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Start a VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.start_vm(db_vm.name)
            if success:
                db_vm.status = 'running'
                self.db.commit()
                
                # Refresh IP addresses after start
                self._refresh_vm_ips(db_vm)
            return success
    
    def stop_vm(self, vm_id: int, user_id: int, force: bool = False, is_superuser: bool = False) -> bool:
        """Stop a VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.stop_vm(db_vm.name, force)
            if success:
                db_vm.status = 'stopped'
                self.db.commit()
            return success
    
    def reboot_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Reboot a VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.reboot_vm(db_vm.name)
            if success:
                self._refresh_vm_ips(db_vm)
            return success
    
    def pause_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Pause a VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.pause_vm(db_vm.name)
            if success:
                db_vm.status = 'paused'
                self.db.commit()
            return success
    
    def resume_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Resume a paused VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            raise ValueError("VM not found")
        
        with LibvirtService() as libvirt:
            success = libvirt.resume_vm(db_vm.name)
            if success:
                db_vm.status = 'running'
                self.db.commit()
            return success
    
    # ============================================
    # VM Deletion
    # ============================================
    
    def delete_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> bool:
        """Delete a VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            raise ValueError("VM not found")
        
        vm_name = db_vm.name
        
        # Delete OVN port if exists
        if db_vm.vpc_id and db_vm.private_ip:
            try:
                vpc = self.db.query(Network).get(db_vm.vpc_id)
                if vpc:
                    tenant_name = self._get_tenant_name(db_vm.owner_id)
                    self.ovn.delete_vm_port(
                        tenant_name=tenant_name,
                        vm_name=vm_name
                    )
            except Exception as e:
                print(f"Warning: Failed to delete OVN port: {e}")
        
        # Delete from libvirt
        with LibvirtService() as libvirt:
            try:
                libvirt.delete_vm(vm_name)
            except Exception as e:
                print(f"Warning: Failed to delete VM from libvirt: {e}")
        
        # Delete security group associations
        self.db.query(VMSecurityGroup).filter(VMSecurityGroup.vm_id == vm_id).delete()
        
        # Delete SSH key associations (if you have this table)
        # self.db.query(VMSSHKey).filter(VMSSHKey.vm_id == vm_id).delete()
        
        # Delete VM from database
        self.db.delete(db_vm)
        self.db.commit()
        
        return True
    
    # ============================================
    # Network Operations
    # ============================================
    
    def attach_network(self, vm_id: int, vpc_id: int, subnet_id: int, user_id: int, private_ip: Optional[str] = None) -> Dict[str, Any]:
        """Attach VM to a VPC network"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        vpc = self.db.query(Network).filter(
            Network.id == vpc_id,
            Network.owner_id == user_id
        ).first()
        if not vpc:
            raise ValueError("VPC not found")
        
        subnet = self.db.query(Subnet).filter(
            Subnet.id == subnet_id,
            Subnet.vpc_id == vpc_id
        ).first()
        if not subnet:
            raise ValueError("Subnet not found")
        
        if not private_ip:
            private_ip = self._allocate_ip_from_subnet(subnet_id, user_id)
        
        # Create OVN port
        tenant_name = self._get_tenant_name(user_id)
        self.ovn.create_vm_port(
            tenant_name=tenant_name,
            vm_name=db_vm.name,
            private_ip=private_ip,
            vni=vpc.vni
        )
        
        # Update VM
        db_vm.vpc_id = vpc_id
        db_vm.subnet_id = subnet_id
        db_vm.private_ip = private_ip
        self.db.commit()
        
        return {'vpc_id': vpc_id, 'subnet_id': subnet_id, 'private_ip': private_ip}
    
    def detach_network(self, vm_id: int, user_id: int) -> bool:
        """Detach VM from network"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        if db_vm.vpc_id and db_vm.private_ip:
            vpc = self.db.query(Network).get(db_vm.vpc_id)
            if vpc:
                tenant_name = self._get_tenant_name(user_id)
                self.ovn.delete_vm_port(tenant_name=tenant_name, vm_name=db_vm.name)
        
        db_vm.vpc_id = None
        db_vm.subnet_id = None
        db_vm.private_ip = None
        db_vm.floating_ip = None
        self.db.commit()
        
        return True
    
    def assign_floating_ip(self, vm_id: int, floating_ip: str, user_id: int) -> bool:
        """Assign floating IP to VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        if not db_vm.private_ip:
            raise ValueError("VM must have a private IP first")
        
        # Create NAT rule in OVN
        tenant_name = self._get_tenant_name(user_id)
        self.ovn.assign_floating_ip(
            tenant_name=tenant_name,
            vm_name=db_vm.name,
            floating_ip=floating_ip,
            private_ip=db_vm.private_ip
        )
        
        db_vm.floating_ip = floating_ip
        self.db.commit()
        
        return True
    
    def remove_floating_ip(self, vm_id: int, user_id: int) -> bool:
        """Remove floating IP from VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        if db_vm.floating_ip:
            # Remove NAT rule
            tenant_name = self._get_tenant_name(user_id)
            self.ovn.remove_floating_ip(
                tenant_name=tenant_name,
                vm_name=db_vm.name,
                floating_ip=db_vm.floating_ip
            )
        
        db_vm.floating_ip = None
        self.db.commit()
        
        return True
    
    # ============================================
    # Security Group Operations
    # ============================================
    
    def attach_security_groups(self, vm_id: int, security_group_ids: List[int], user_id: int) -> bool:
        """Attach security groups to VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        return self._attach_security_groups(vm_id, security_group_ids, user_id)
    
    def detach_security_group(self, vm_id: int, security_group_id: int, user_id: int) -> bool:
        """Detach a security group from VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        self.db.query(VMSecurityGroup).filter(
            VMSecurityGroup.vm_id == vm_id,
            VMSecurityGroup.security_group_id == security_group_id
        ).delete()
        self.db.commit()
        
        # Re-sync firewall rules
        self._sync_firewall_rules(vm_id)
        
        return True
    
    def list_security_groups(self, vm_id: int, user_id: int) -> List[Dict[str, Any]]:
        """List security groups attached to VM"""
        db_vm = self._get_authorized_vm(vm_id, user_id)
        if not db_vm:
            raise ValueError("VM not found")
        
        assignments = self.db.query(VMSecurityGroup).filter(VMSecurityGroup.vm_id == vm_id).all()
        
        security_groups = []
        for assignment in assignments:
            sg = self.db.query(SecurityGroup).get(assignment.security_group_id)
            if sg:
                security_groups.append({
                    'id': sg.id,
                    'name': sg.name,
                    'description': sg.description
                })
        
        return security_groups
    
    # ============================================
    # Console Access
    # ============================================
    
    def get_console(self, vm_id: int, user_id: int, is_superuser: bool = False) -> Optional[Dict[str, Any]]:
        """Get VNC/SPICE console URL"""
        db_vm = self._get_authorized_vm(vm_id, user_id, is_superuser)
        if not db_vm:
            return None
        
        with LibvirtService() as libvirt:
            return libvirt.get_console_url(db_vm.name)
    
    # ============================================
    # Private Helper Methods
    # ============================================
    
    def _get_authorized_vm(self, vm_id: int, user_id: int, is_superuser: bool = False) -> Optional[VM]:
        """Get VM with authorization check"""
        query = self.db.query(VM).filter(VM.id == vm_id)
        if not is_superuser:
            query = query.filter(VM.owner_id == user_id)
        return query.first()
    
    def _get_tenant_name(self, user_id: int) -> str:
        """Get tenant name from user_id"""
        from app.models.database import User
        user = self.db.query(User).get(user_id)
        return user.username if user else f"user-{user_id}"
    
    def _allocate_ip_from_subnet(self, subnet_id: int, user_id: int) -> Optional[str]:
        """Allocate next available IP from subnet"""
        from app.services.vpc_service import VPCService
        vpc_service = VPCService(self.db)
        available = vpc_service.get_available_ips(subnet_id, user_id)
        if available and available.get('available_list'):
            return available['available_list'][0]
        return None
    
    def _attach_security_groups(self, vm_id: int, security_group_ids: List[int], user_id: int) -> bool:
        """Attach security groups to VM"""
        for sg_id in security_group_ids:
            sg = self.db.query(SecurityGroup).filter(
                SecurityGroup.id == sg_id,
                SecurityGroup.owner_id == user_id
            ).first()
            if sg:
                existing = self.db.query(VMSecurityGroup).filter(
                    VMSecurityGroup.vm_id == vm_id,
                    VMSecurityGroup.security_group_id == sg_id
                ).first()
                if not existing:
                    vm_sg = VMSecurityGroup(vm_id=vm_id, security_group_id=sg_id)
                    self.db.add(vm_sg)
        
        self.db.commit()
        self._sync_firewall_rules(vm_id)
        return True
    
    def _attach_ssh_keys(self, vm_id: int, ssh_key_ids: List[int], user_id: int) -> bool:
        """Attach SSH keys to VM (implement if you have VMSSHKey table)"""
        # Implement if you have SSH key association table
        return True
    
    def _sync_firewall_rules(self, vm_id: int):
        """Sync firewall rules for VM"""
        from app.services.firewall_service import FirewallService
        firewall_service = FirewallService(self.db)
        firewall_service._sync_vm_acls(vm_id)
    
    def _refresh_vm_ips(self, db_vm: VM):
        """Refresh VM IP addresses from libvirt"""
        with LibvirtService() as libvirt:
            vm_info = libvirt.get_vm(db_vm.name)
            if vm_info and vm_info.get('ip_addresses'):
                # Update private IP if changed
                for ip in vm_info['ip_addresses']:
                    if ip.startswith('10.') or ip.startswith('172.') or ip.startswith('192.'):
                        if ip != db_vm.private_ip:
                            db_vm.private_ip = ip
                            self.db.commit()
                        break
    
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
            
            if db_vm.vpc_id:
                vpc = self.db.query(Network).filter(Network.id == db_vm.vpc_id).first()
                if vpc:
                    vm_data['vpc_name'] = vpc.name
                    vm_data['vpc_cidr'] = vpc.cidr
            
            if db_vm.subnet_id:
                subnet = self.db.query(Subnet).filter(Subnet.id == db_vm.subnet_id).first()
                if subnet:
                    vm_data['subnet_name'] = subnet.name
                    vm_data['subnet_cidr'] = subnet.cidr
            
            security_groups = []
            assignments = self.db.query(VMSecurityGroup).filter(VMSecurityGroup.vm_id == db_vm.id).all()
            for assignment in assignments:
                sg = self.db.query(SecurityGroup).get(assignment.security_group_id)
                if sg:
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