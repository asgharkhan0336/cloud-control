"""Floating IP Service - Assign/Release public IPs"""

from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.database import FloatingIP, VM, PublicSubnet
from app.services.ovn_service import OVNService

class FloatingIPService:
    def __init__(self, db: Session):
        self.db = db
        self.ovn = OVNService()
    
    def assign_floating_ip(self, vm_name: str, subnet_id: Optional[int] = None) -> Dict:
        """Assign a floating IP to a VM"""
        
        # Check if VM exists
        vm = self.db.query(VM).filter(VM.name == vm_name).first()
        if not vm:
            raise ValueError(f"VM {vm_name} not found")
        
        if not vm.private_ip:
            raise ValueError(f"VM {vm_name} has no private IP")
        
        # Check if VM already has floating IP
        existing = self.db.query(FloatingIP).filter(
            FloatingIP.vm_name == vm_name,
            FloatingIP.is_allocated == True
        ).first()
        
        if existing:
            raise ValueError(f"VM {vm_name} already has floating IP: {existing.ip_address}")
        
        # Find available floating IP
        query = self.db.query(FloatingIP).filter(FloatingIP.is_allocated == False)
        if subnet_id:
            query = query.filter(FloatingIP.subnet_id == subnet_id)
        
        floating_ip = query.first()
        if not floating_ip:
            raise ValueError("No available floating IPs")
        
        try:
            # Create NAT rule in OVN
            self.ovn.assign_floating_ip(
                tenant_name=vm.owner.username,
                vm_name=vm_name,
                floating_ip=floating_ip.ip_address,
                private_ip=vm.private_ip
            )
            
            # Update database
            floating_ip.vm_name = vm_name
            floating_ip.is_allocated = True
            floating_ip.allocated_at = func.now()
            
            vm.floating_ip = floating_ip.ip_address
            
            self.db.commit()
            
            return {
                "assigned": True,
                "floating_ip": floating_ip.ip_address,
                "vm_name": vm_name,
                "private_ip": vm.private_ip,
                "subnet_id": floating_ip.subnet_id
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to assign floating IP: {e}")
    
    def release_floating_ip(self, ip_address: str) -> Dict:
        """Release a floating IP"""
        
        floating_ip = self.db.query(FloatingIP).filter(
            FloatingIP.ip_address == ip_address
        ).first()
        
        if not floating_ip:
            raise ValueError(f"Floating IP {ip_address} not found")
        
        if not floating_ip.is_allocated:
            raise ValueError(f"Floating IP {ip_address} is not allocated")
        
        vm_name = floating_ip.vm_name
        
        try:
            # Remove NAT rule from OVN
            # (Implementation depends on how OVN service tracks rules)
            
            # Update database
            vm = self.db.query(VM).filter(VM.name == vm_name).first()
            if vm:
                vm.floating_ip = None
            
            floating_ip.vm_name = None
            floating_ip.is_allocated = False
            floating_ip.allocated_at = None
            
            self.db.commit()
            
            return {
                "released": True,
                "floating_ip": ip_address,
                "vm_name": vm_name
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to release floating IP: {e}")