"""VPC Service - Virtual Private Cloud Management"""

import ipaddress
import subprocess
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import Network, Subnet, VM, VPCPeering, User

class VPCService:
    def __init__(self, db: Session):
        self.db = db
    
    def _run_ovn(self, cmd: list) -> str:
        """Execute OVN command"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"OVN Error: {result.stderr}")
        return result.stdout.strip()
    
    # ============================================
    # VPC Operations
    # ============================================
    
    def create_vpc(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        cidr: Optional[str] = None
    ) -> Dict:
        """Create a new VPC"""
        
        # Check if name exists for user
        existing = self.db.query(Network).filter(
            and_(Network.owner_id == user_id, Network.name == name)
        ).first()
        
        if existing:
            raise ValueError(f"VPC with name '{name}' already exists")
        
        # Allocate subnet if not provided
        if not cidr:
            cidr = self._allocate_subnet(user_id)
        
        # Parse network
        network = ipaddress.ip_network(cidr, strict=False)
        gateway = str(list(network.hosts())[0])
        
        # Allocate VNI
        vni = self._allocate_vni()
        
        # Create OVN logical switch
        switch_name = f"vpc-{user_id}-{name}".replace(' ', '-').lower()
        try:
            self._run_ovn(["ovn-nbctl", "ls-add", switch_name])
            self._run_ovn(["ovn-nbctl", "set", "logical_switch", switch_name, 
                           f"external_ids:geneve_vni={vni}"])
        except Exception as e:
            raise Exception(f"Failed to create OVN switch: {str(e)}")
        
        # Create VPC in database
        vpc = Network(
            name=name,
            description=description,
            owner_id=user_id,
            cidr=cidr,
            gateway=gateway,
            vni=vni,
            is_default=False
        )
        self.db.add(vpc)
        self.db.commit()
        self.db.refresh(vpc)
        
        # Create default subnet
        self._create_default_subnet(vpc.id, cidr, gateway)
        
        return self._format_vpc(vpc)
    
    def get_vpc(self, vpc_id: int, user_id: int) -> Optional[Dict]:
        """Get VPC by ID"""
        vpc = self.db.query(Network).filter(
            and_(Network.id == vpc_id, Network.owner_id == user_id)
        ).first()
        
        if not vpc:
            return None
        
        return self._format_vpc(vpc)
    
    def list_user_vpcs(self, user_id: int) -> List[Dict]:
        """List all VPCs for a user"""
        vpcs = self.db.query(Network).filter(Network.owner_id == user_id).all()
        return [self._format_vpc(vpc) for vpc in vpcs]
    
    def delete_vpc(self, vpc_id: int, user_id: int) -> Dict:
        """Delete a VPC"""
        vpc = self.db.query(Network).filter(
            and_(Network.id == vpc_id, Network.owner_id == user_id)
        ).first()
        
        if not vpc:
            raise ValueError(f"VPC not found")
        
        if vpc.is_default:
            raise ValueError("Cannot delete default VPC")
        
        # Check for VMs
        vm_count = self.db.query(VM).filter(VM.vpc_id == vpc_id).count()
        if vm_count > 0:
            raise ValueError(f"Cannot delete VPC with {vm_count} VMs")
        
        # Delete OVN switch
        switch_name = f"vpc-{user_id}-{vpc.name}".replace(' ', '-').lower()
        try:
            self._run_ovn(["ovn-nbctl", "ls-del", switch_name])
        except:
            pass
        
        # Delete from database
        self.db.delete(vpc)
        self.db.commit()
        
        return {"success": True, "message": f"VPC '{vpc.name}' deleted"}
    
    # ============================================
    # Subnet Operations
    # ============================================
    
    def create_subnet(
        self,
        vpc_id: int,
        user_id: int,
        name: str,
        cidr: str,
        is_public: bool = False
    ) -> Dict:
        """Create a subnet within a VPC"""
        
        # Verify VPC ownership
        vpc = self.db.query(Network).filter(
            and_(Network.id == vpc_id, Network.owner_id == user_id)
        ).first()
        
        if not vpc:
            raise ValueError("VPC not found")
        
        # Check if subnet CIDR is within VPC CIDR
        vpc_network = ipaddress.ip_network(vpc.cidr)
        subnet_network = ipaddress.ip_network(cidr)
        
        if not subnet_network.subnet_of(vpc_network):
            raise ValueError(f"Subnet must be within VPC CIDR: {vpc.cidr}")
        
        # Check for overlapping subnets
        existing_subnets = self.db.query(Subnet).filter(Subnet.vpc_id == vpc_id).all()
        for existing in existing_subnets:
            existing_net = ipaddress.ip_network(existing.cidr)
            if subnet_network.overlaps(existing_net):
                raise ValueError(f"Subnet overlaps with existing subnet: {existing.cidr}")
        
        # Check name uniqueness within VPC
        existing_name = self.db.query(Subnet).filter(
            and_(Subnet.vpc_id == vpc_id, Subnet.name == name)
        ).first()
        if existing_name:
            raise ValueError(f"Subnet with name '{name}' already exists in this VPC")
        
        # Get gateway (first usable IP)
        hosts = list(subnet_network.hosts())
        gateway = str(hosts[0]) if hosts else None
        
        # Create subnet
        subnet = Subnet(
            name=name,
            vpc_id=vpc_id,
            cidr=cidr,
            gateway=gateway,
            is_public=is_public
        )
        self.db.add(subnet)
        self.db.commit()
        self.db.refresh(subnet)
        
        return self._format_subnet(subnet)
    
    def list_subnets(self, vpc_id: int, user_id: int) -> List[Dict]:
        """List all subnets in a VPC"""
        vpc = self.db.query(Network).filter(
            and_(Network.id == vpc_id, Network.owner_id == user_id)
        ).first()
        
        if not vpc:
            raise ValueError("VPC not found")
        
        subnets = self.db.query(Subnet).filter(Subnet.vpc_id == vpc_id).all()
        return [self._format_subnet(subnet) for subnet in subnets]
    
    def list_all_user_subnets(self, user_id: int) -> List[Dict]:
        """List all subnets for a user across all VPCs"""
        subnets = self.db.query(Subnet).join(Network).filter(
            Network.owner_id == user_id
        ).all()
        return [self._format_subnet(subnet) for subnet in subnets]
    
    def get_subnet(self, subnet_id: int, user_id: int) -> Optional[Dict]:
        """Get subnet by ID"""
        subnet = self.db.query(Subnet).join(Network).filter(
            and_(Subnet.id == subnet_id, Network.owner_id == user_id)
        ).first()
        
        if not subnet:
            return None
        
        return self._format_subnet(subnet)
    
    def delete_subnet(self, subnet_id: int, user_id: int) -> Dict:
        """Delete a subnet"""
        subnet = self.db.query(Subnet).join(Network).filter(
            and_(Subnet.id == subnet_id, Network.owner_id == user_id)
        ).first()
        
        if not subnet:
            raise ValueError("Subnet not found")
        
        # Check for VMs in subnet
        vm_count = self.db.query(VM).filter(VM.subnet_id == subnet_id).count()
        if vm_count > 0:
            raise ValueError(f"Cannot delete subnet with {vm_count} VMs")
        
        self.db.delete(subnet)
        self.db.commit()
        
        return {"success": True, "message": f"Subnet '{subnet.name}' deleted"}
    
    def get_available_ips(self, subnet_id: int, user_id: int) -> Dict:
        """Get available IP addresses in a subnet"""
        subnet = self.db.query(Subnet).join(Network).filter(
            and_(Subnet.id == subnet_id, Network.owner_id == user_id)
        ).first()
        
        if not subnet:
            raise ValueError("Subnet not found")
        
        network = ipaddress.ip_network(subnet.cidr)
        hosts = list(network.hosts())
        
        # Get used IPs
        used_ips = set()
        vms = self.db.query(VM).filter(VM.subnet_id == subnet_id).all()
        for vm in vms:
            if vm.private_ip:
                used_ips.add(vm.private_ip)
        
        # Gateway is also used
        used_ips.add(subnet.gateway)
        
        available = [str(ip) for ip in hosts if str(ip) not in used_ips]
        
        return {
            "subnet_id": subnet_id,
            "subnet_name": subnet.name,
            "cidr": subnet.cidr,
            "total_ips": len(hosts),
            "used_ips": len(used_ips),
            "available_ips": len(available),
            "available_list": available[:20]
        }
    
    # ============================================
    # VPC Peering Operations
    # ============================================
    
    def create_peering(self, vpc_id: int, peer_vpc_id: int, user_id: int) -> Dict:
        """Create VPC peering request"""
        
        # Verify ownership of source VPC
        vpc = self.db.query(Network).filter(
            and_(Network.id == vpc_id, Network.owner_id == user_id)
        ).first()
        
        if not vpc:
            raise ValueError("Source VPC not found")
        
        # Verify peer VPC exists
        peer_vpc = self.db.query(Network).filter(Network.id == peer_vpc_id).first()
        if not peer_vpc:
            raise ValueError("Peer VPC not found")
        
        # Cannot peer with itself
        if vpc_id == peer_vpc_id:
            raise ValueError("Cannot peer a VPC with itself")
        
        # Check if peering already exists
        existing = self.db.query(VPCPeering).filter(
            ((VPCPeering.vpc_a_id == vpc_id) & (VPCPeering.vpc_b_id == peer_vpc_id)) |
            ((VPCPeering.vpc_a_id == peer_vpc_id) & (VPCPeering.vpc_b_id == vpc_id))
        ).first()
        
        if existing:
            raise ValueError("VPC peering already exists")
        
        # Create peering
        peering = VPCPeering(
            vpc_a_id=vpc_id,
            vpc_b_id=peer_vpc_id,
            status="pending"
        )
        self.db.add(peering)
        self.db.commit()
        self.db.refresh(peering)
        
        return self._format_peering(peering)
    
    def accept_peering(self, peering_id: int, user_id: int) -> Dict:
        """Accept VPC peering request"""
        
        peering = self.db.query(VPCPeering).join(
            Network, VPCPeering.vpc_b_id == Network.id
        ).filter(
            and_(VPCPeering.id == peering_id, Network.owner_id == user_id)
        ).first()
        
        if not peering:
            raise ValueError("Peering request not found")
        
        if peering.status != "pending":
            raise ValueError(f"Peering is already {peering.status}")
        
        # Create OVN patch between VPCs
        vpc_a = self.db.query(Network).get(peering.vpc_a_id)
        vpc_b = self.db.query(Network).get(peering.vpc_b_id)
        
        switch_a = f"vpc-{vpc_a.owner_id}-{vpc_a.name}".replace(' ', '-').lower()
        switch_b = f"vpc-{vpc_b.owner_id}-{vpc_b.name}".replace(' ', '-').lower()
        
        patch_a = f"patch-{vpc_a.id}-to-{vpc_b.id}"
        patch_b = f"patch-{vpc_b.id}-to-{vpc_a.id}"
        
        try:
            # Create patch ports
            self._run_ovn(["ovn-nbctl", "lsp-add", switch_a, patch_a])
            self._run_ovn(["ovn-nbctl", "lsp-set-addresses", patch_a, "router"])
            self._run_ovn(["ovn-nbctl", "lsp-set-type", patch_a, "patch"])
            self._run_ovn(["ovn-nbctl", "lsp-set-options", patch_a, f"peer={patch_b}"])
            
            self._run_ovn(["ovn-nbctl", "lsp-add", switch_b, patch_b])
            self._run_ovn(["ovn-nbctl", "lsp-set-addresses", patch_b, "router"])
            self._run_ovn(["ovn-nbctl", "lsp-set-type", patch_b, "patch"])
            self._run_ovn(["ovn-nbctl", "lsp-set-options", patch_b, f"peer={patch_a}"])
        except Exception as e:
            raise Exception(f"Failed to create OVN patch: {str(e)}")
        
        # Update peering status
        peering.status = "active"
        peering.accepted_at = func.now()
        self.db.commit()
        
        return self._format_peering(peering)
    
    def list_peerings(self, vpc_id: int, user_id: int) -> List[Dict]:
        """List all peerings for a VPC"""
        vpc = self.db.query(Network).filter(
            and_(Network.id == vpc_id, Network.owner_id == user_id)
        ).first()
        
        if not vpc:
            raise ValueError("VPC not found")
        
        peerings = self.db.query(VPCPeering).filter(
            (VPCPeering.vpc_a_id == vpc_id) | (VPCPeering.vpc_b_id == vpc_id)
        ).all()
        
        return [self._format_peering(p) for p in peerings]
    
    # ============================================
    # Helper Methods
    # ============================================
    
    def _allocate_subnet(self, user_id: int) -> str:
        """Allocate next available /24 subnet"""
        used_subnets = [n.cidr for n in self.db.query(Network).all()]
        
        base_networks = ["10.0.0.0/16", "172.16.0.0/16", "192.168.0.0/16"]
        
        for base in base_networks:
            base_net = ipaddress.ip_network(base)
            for subnet in base_net.subnets(new_prefix=24):
                if str(subnet) not in used_subnets:
                    return str(subnet)
        
        raise ValueError("No available subnets")
    
    def _allocate_vni(self) -> int:
        """Allocate unique VNI"""
        used_vnis = set(n.vni for n in self.db.query(Network).all() if n.vni)
        
        for vni in range(10000, 11000):
            if vni not in used_vnis:
                return vni
        
        raise ValueError("No available VNIs")
    
    def _create_default_subnet(self, vpc_id: int, cidr: str, gateway: str):
        """Create default subnet for VPC"""
        subnet = Subnet(
            name="default",
            vpc_id=vpc_id,
            cidr=cidr,
            gateway=gateway,
            is_public=False
        )
        self.db.add(subnet)
        self.db.commit()
    
    def _format_vpc(self, vpc: Network) -> Dict:
        """Format VPC for API response"""
        vm_count = self.db.query(VM).filter(VM.vpc_id == vpc.id).count()
        subnet_count = self.db.query(Subnet).filter(Subnet.vpc_id == vpc.id).count()
        
        return {
            "id": vpc.id,
            "name": vpc.name,
            "description": vpc.description,
            "cidr": vpc.cidr,
            "gateway": vpc.gateway,
            "vni": vpc.vni,
            "is_default": vpc.is_default,
            "created_at": vpc.created_at,
            "vm_count": vm_count,
            "subnet_count": subnet_count
        }
    
    def _format_subnet(self, subnet: Subnet) -> Dict:
        """Format subnet for API response"""
        network = ipaddress.ip_network(subnet.cidr)
        total_ips = len(list(network.hosts()))
        used_ips = self.db.query(VM).filter(VM.subnet_id == subnet.id).count() + 1
        
        return {
            "id": subnet.id,
            "name": subnet.name,
            "vpc_id": subnet.vpc_id,
            "cidr": subnet.cidr,
            "gateway": subnet.gateway,
            "is_public": subnet.is_public,
            "total_ips": total_ips,
            "used_ips": used_ips,
            "available_ips": total_ips - used_ips,
            "created_at": subnet.created_at
        }
    
    def _format_peering(self, peering: VPCPeering) -> Dict:
        """Format peering for API response"""
        return {
            "id": peering.id,
            "vpc_a_id": peering.vpc_a_id,
            "vpc_b_id": peering.vpc_b_id,
            "status": peering.status,
            "created_at": peering.created_at,
            "accepted_at": peering.accepted_at
        }


# Import func for accepted_at
from sqlalchemy.sql import func