"""Floating IP Service - Public IP Assignment Management"""

import ipaddress
import subprocess
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.models.database import FloatingIP, VM, User, Network

class FloatingIPService:
    def __init__(self, db: Session):
        self.db = db
    
    def _run_ovn(self, cmd: list) -> str:
        """Execute OVN command"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"OVN Error: {result.stderr}")
        return result.stdout.strip()
    
    def get_available_ips(self, subnet_id: Optional[int], user_id: int) -> List[Dict]:
        """Get available floating IPs"""
        query = self.db.query(FloatingIP).filter(FloatingIP.is_allocated == False)
        
        if subnet_id:
            query = query.filter(FloatingIP.subnet_id == subnet_id)
        
        ips = query.all()
        return [self._format_floating_ip(ip) for ip in ips]
    
    def list_user_floating_ips(self, user_id: int) -> List[Dict]:
        """List all floating IPs accessible to user"""
        ips = self.db.query(FloatingIP).join(Network).filter(
            Network.owner_id == user_id
        ).all()
        return [self._format_floating_ip(ip) for ip in ips]
    
    def get_floating_ip(self, ip_address: str, user_id: int) -> Optional[Dict]:
        """Get floating IP details"""
        fip = self.db.query(FloatingIP).join(Network).filter(
            and_(FloatingIP.ip_address == ip_address, Network.owner_id == user_id)
        ).first()
        
        if not fip:
            return None
        
        return self._format_floating_ip(fip)
    
    def assign_floating_ip(self, vm_id: int, subnet_id: Optional[int], user_id: int) -> Dict:
        """Assign a floating IP to a VM"""
        
        vm = self.db.query(VM).filter(
            and_(VM.id == vm_id, VM.owner_id == user_id)
        ).first()
        
        if not vm:
            raise ValueError("VM not found")
        
        if not vm.private_ip:
            raise ValueError("VM has no private IP address")
        
        # Check if VM already has a floating IP
        existing = self.db.query(FloatingIP).filter(
            and_(FloatingIP.vm_id == vm_id, FloatingIP.is_allocated == True)
        ).first()
        
        if existing:
            raise ValueError(f"VM already has floating IP: {existing.ip_address}")
        
        # Find available floating IP
        query = self.db.query(FloatingIP).filter(FloatingIP.is_allocated == False)
        if subnet_id:
            query = query.filter(FloatingIP.subnet_id == subnet_id)
        
        fip = query.first()
        if not fip:
            raise ValueError("No available floating IPs")
        
        # Get VPC info for OVN
        vpc = self.db.query(Network).get(vm.vpc_id) if vm.vpc_id else None
        
        try:
            if vpc:
                # Create NAT rule in OVN
                self._run_ovn([
                    "ovn-nbctl", "lr-nat-add", "router-gateway", "dnat_and_snat",
                    fip.ip_address, vm.private_ip, f"port-{vm.name}", 
                    f"02:00:00:{hash(vm.name) % 256:02x}:00:01"
                ])
            
            # Update database
            fip.vm_id = vm_id
            fip.is_allocated = True
            fip.allocated_at = datetime.utcnow()
            
            vm.floating_ip = fip.ip_address
            
            self.db.commit()
            
            return self._format_floating_ip(fip)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to assign floating IP: {str(e)}")
    
    def release_floating_ip(self, ip_address: str, user_id: int) -> Dict:
        """Release a floating IP"""
        
        fip = self.db.query(FloatingIP).join(Network).filter(
            and_(FloatingIP.ip_address == ip_address, Network.owner_id == user_id)
        ).first()
        
        if not fip:
            raise ValueError("Floating IP not found")
        
        if not fip.is_allocated:
            raise ValueError("Floating IP is not allocated")
        
        vm = self.db.query(VM).get(fip.vm_id) if fip.vm_id else None
        
        try:
            # Remove NAT rule from OVN
            if vm:
                # Find and remove NAT rule
                nat_list = self._run_ovn(["ovn-nbctl", "lr-nat-list", "router-gateway"])
                for line in nat_list.split('\n'):
                    if ip_address in line and vm.private_ip in line:
                        # Extract NAT UUID and delete
                        nat_uuid = line.split()[0]
                        self._run_ovn(["ovn-nbctl", "lr-nat-del", "router-gateway", nat_uuid])
                        break
            
            # Update database
            if vm:
                vm.floating_ip = None
            
            fip.vm_id = None
            fip.is_allocated = False
            fip.allocated_at = None
            
            self.db.commit()
            
            return {"success": True, "message": f"Floating IP {ip_address} released"}
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to release floating IP: {str(e)}")
    
    def _format_floating_ip(self, fip: FloatingIP) -> Dict:
        """Format floating IP for API response"""
        return {
            "id": fip.id,
            "ip_address": fip.ip_address,
            "subnet_id": fip.subnet_id,
            "vm_id": fip.vm_id,
            "vm_name": fip.vm.name if fip.vm else None,
            "is_allocated": fip.is_allocated,
            "allocated_at": fip.allocated_at,
            "created_at": fip.created_at
        }