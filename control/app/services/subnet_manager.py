"""Subnet Pool Manager - Allocates /28 subnets to tenants"""

import ipaddress
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.database import Network

class SubnetManager:
    # Available private IP space (RFC 1918)
    SUBNET_POOLS = [
        "10.0.0.0/20",     # 10.0.0.0 - 10.0.15.255 (4096 IPs)
        "10.1.0.0/20",     # 10.1.0.0 - 10.1.15.255 (4096 IPs)
        "172.16.0.0/20",   # 172.16.0.0 - 172.16.15.255 (4096 IPs)
    ]
    
    TENANT_SUBNET_SIZE = 28  # /28 = 16 IPs, 14 usable (perfect for small tenants)
    
    def __init__(self, db: Session):
        self.db = db
        
    def get_used_subnets(self) -> List[str]:
        """Get all allocated subnets from database"""
        networks = self.db.query(Network).all()
        return [n.cidr for n in networks]
    
    def allocate_subnet(self, tenant_id: int) -> Optional[str]:
        """Allocate next available /28 subnet"""
        used = self.get_used_subnets()
        used_networks = [ipaddress.ip_network(u) for u in used]
        
        for pool_cidr in self.SUBNET_POOLS:
            pool = ipaddress.ip_network(pool_cidr)
            
            # Iterate through /28 subnets in this pool
            for subnet in pool.subnets(new_prefix=self.TENANT_SUBNET_SIZE):
                # Check if subnet overlaps with any used subnet
                overlaps = False
                for used_net in used_networks:
                    if subnet.overlaps(used_net):
                        overlaps = True
                        break
                
                if not overlaps:
                    return str(subnet)
        
        return None  # No available subnets
    
    def get_subnet_info(self, cidr: str) -> dict:
        """Get detailed information about a subnet"""
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = list(network.hosts())
        
        return {
            "cidr": str(network),
            "netmask": str(network.netmask),
            "gateway": str(hosts[0]) if hosts else None,
            "first_usable": str(hosts[1]) if len(hosts) > 1 else None,
            "last_usable": str(hosts[-1]) if hosts else None,
            "broadcast": str(network.broadcast_address),
            "total_ips": network.num_addresses,
            "usable_ips": len(hosts),
            "dhcp_pool_start": str(hosts[1]) if len(hosts) > 1 else None,
            "dhcp_pool_end": str(hosts[-1]) if hosts else None
        }
    
    def allocate_ip_for_vm(self, network_cidr: str, vm_name: str) -> Optional[str]:
        """Allocate specific IP for VM from tenant's subnet"""
        from app.models.database import VM
        
        network = ipaddress.ip_network(network_cidr, strict=False)
        hosts = list(network.hosts())
        
        # Skip gateway (first IP)
        available_ips = hosts[1:]
        
        # Get used IPs in this network
        used_ips = []
        vms = self.db.query(VM).filter(VM.network_name == f"tenant-{vm_name.split('-')[0]}").all()
        for vm in vms:
            if vm.private_ip:
                used_ips.append(vm.private_ip)
        
        # Find first available IP
        for ip in available_ips:
            if str(ip) not in used_ips:
                return str(ip)
        
        return None
