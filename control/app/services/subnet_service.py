"""Public Subnet Service - Manages multiple public subnets dynamically"""

import ipaddress
import subprocess
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import PublicSubnet, FloatingIP

class PublicSubnetService:
    """API-driven public subnet management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.router = "router-gateway"
    
    def _run_ovn(self, cmd: List[str]) -> str:
        """Execute OVN command"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"OVN Error: {result.stderr}")
        return result.stdout.strip()
    
    def add_public_subnet(self, name: str, cidr: str, gateway: str) -> Dict:
        """
        Add a new public subnet to the platform
        This creates OVN logical switch and connects to router
        """
        
        # Validate CIDR
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = list(network.hosts())
        
        # Calculate router IP (first usable IP after gateway)
        router_ip = str(hosts[0]) if hosts[0] != ipaddress.ip_address(gateway) else str(hosts[1])
        
        # Check if subnet already exists
        existing = self.db.query(PublicSubnet).filter(
            (PublicSubnet.name == name) | (PublicSubnet.cidr == cidr)
        ).first()
        
        if existing:
            raise ValueError(f"Subnet {name} or {cidr} already exists")
        
        try:
            # 1. Create OVN logical switch
            switch_name = f"ls-{name}"
            self._run_ovn(["ovn-nbctl", "ls-add", switch_name])
            
            # 2. Add localnet port
            self._run_ovn(["ovn-nbctl", "lsp-add", switch_name, f"ln-{name}"])
            self._run_ovn(["ovn-nbctl", "lsp-set-addresses", f"ln-{name}", "unknown"])
            self._run_ovn(["ovn-nbctl", "lsp-set-type", f"ln-{name}", "localnet"])
            self._run_ovn(["ovn-nbctl", "lsp-set-options", f"ln-{name}", "network_name=external"])
            
            # 3. Connect router to this subnet
            router_port = f"lrp-{name}"
            router_mac = f"02:00:00:{hash(name) % 256:02x}:{hash(cidr) % 256:02x}:01"
            
            self._run_ovn(["ovn-nbctl", "lrp-add", self.router, router_port,
                          router_mac, f"{router_ip}/{network.prefixlen}"])
            
            switch_port = f"lsp-{name}-router"
            self._run_ovn(["ovn-nbctl", "lsp-add", switch_name, switch_port])
            self._run_ovn(["ovn-nbctl", "lsp-set-type", switch_port, "router"])
            self._run_ovn(["ovn-nbctl", "lsp-set-addresses", switch_port, "router"])
            self._run_ovn(["ovn-nbctl", "lsp-set-options", switch_port, f"router-port={router_port}"])
            
            # 4. Add route to gateway
            self._run_ovn(["ovn-nbctl", "lr-route-add", self.router, "0.0.0.0/0", gateway])
            
            # 5. Save to database
            db_subnet = PublicSubnet(
                name=name,
                cidr=cidr,
                gateway=gateway,
                router_ip=router_ip,
                available_ips=len(hosts) - 2  # Exclude gateway and router IP
            )
            self.db.add(db_subnet)
            self.db.commit()
            self.db.refresh(db_subnet)
            
            # 6. Create floating IP pool for this subnet
            self._create_floating_ip_pool(db_subnet.id, cidr, gateway, router_ip)
            
            return {
                "id": db_subnet.id,
                "name": name,
                "cidr": cidr,
                "gateway": gateway,
                "router_ip": router_ip,
                "available_ips": db_subnet.available_ips,
                "switch": switch_name
            }
            
        except Exception as e:
            # Rollback OVN changes if database fails
            self._cleanup_ovn_subnet(name)
            raise Exception(f"Failed to add subnet: {e}")
    
    def _create_floating_ip_pool(self, subnet_id: int, cidr: str, 
                                  gateway: str, router_ip: str):
        """Create floating IP pool from subnet"""
        network = ipaddress.ip_network(cidr, strict=False)
        
        for ip in network.hosts():
            ip_str = str(ip)
            # Skip gateway and router IP
            if ip_str == gateway or ip_str == router_ip:
                continue
            
            floating_ip = FloatingIP(
                ip_address=ip_str,
                subnet_id=subnet_id,
                is_allocated=False
            )
            self.db.add(floating_ip)
        
        self.db.commit()
    
    def remove_public_subnet(self, subnet_id: int) -> Dict:
        """Remove a public subnet"""
        
        subnet = self.db.query(PublicSubnet).filter(PublicSubnet.id == subnet_id).first()
        if not subnet:
            raise ValueError(f"Subnet {subnet_id} not found")
        
        # Check if any floating IPs are allocated
        allocated = self.db.query(FloatingIP).filter(
            FloatingIP.subnet_id == subnet_id,
            FloatingIP.is_allocated == True
        ).count()
        
        if allocated > 0:
            raise ValueError(f"Cannot delete subnet with {allocated} allocated floating IPs")
        
        try:
            # Remove OVN configuration
            self._cleanup_ovn_subnet(subnet.name)
            
            # Delete from database
            self.db.query(FloatingIP).filter(FloatingIP.subnet_id == subnet_id).delete()
            self.db.delete(subnet)
            self.db.commit()
            
            return {"removed": True, "subnet": subnet.name}
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to remove subnet: {e}")
    
    def _cleanup_ovn_subnet(self, name: str):
        """Clean up OVN resources for a subnet"""
        try:
            switch_name = f"ls-{name}"
            router_port = f"lrp-{name}"
            
            # Remove router port
            self._run_ovn(["ovn-nbctl", "lrp-del", router_port])
            
            # Remove logical switch
            self._run_ovn(["ovn-nbctl", "ls-del", switch_name])
            
        except:
            pass  # Already removed
    
    def list_public_subnets(self) -> List[Dict]:
        """List all public subnets"""
        subnets = self.db.query(PublicSubnet).all()
        
        result = []
        for subnet in subnets:
            allocated = self.db.query(FloatingIP).filter(
                FloatingIP.subnet_id == subnet.id,
                FloatingIP.is_allocated == True
            ).count()
            
            result.append({
                "id": subnet.id,
                "name": subnet.name,
                "cidr": subnet.cidr,
                "gateway": subnet.gateway,
                "router_ip": subnet.router_ip,
                "total_ips": subnet.available_ips + allocated,
                "allocated_ips": allocated,
                "available_ips": subnet.available_ips - allocated,
                "created_at": subnet.created_at.isoformat() if subnet.created_at else None
            })
        
        return result
    
    def get_available_floating_ips(self, subnet_id: Optional[int] = None) -> List[Dict]:
        """Get available floating IPs"""
        query = self.db.query(FloatingIP).filter(FloatingIP.is_allocated == False)
        
        if subnet_id:
            query = query.filter(FloatingIP.subnet_id == subnet_id)
        
        ips = query.all()
        
        return [{
            "id": ip.id,
            "ip_address": ip.ip_address,
            "subnet_id": ip.subnet_id
        } for ip in ips]