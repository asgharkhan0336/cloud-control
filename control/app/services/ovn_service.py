"""OVN Service - Creates tenant networks with allocated subnets"""

import subprocess
import ipaddress
import random
from typing import Dict, Optional

class OVNService:
    def __init__(self):
        self.router = "router-public"
    
    def _run(self, cmd: list) -> str:
        """Run OVN command"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"OVN Error: {result.stderr}")
        return result.stdout.strip()
    
    def create_tenant_network(self, tenant_name: str, subnet_cidr: str, 
                              vxlan_id: int) -> Dict:
        """Create isolated tenant network"""
        
        switch_name = f"tenant-{tenant_name}"
        network = ipaddress.ip_network(subnet_cidr, strict=False)
        hosts = list(network.hosts())
        gateway_ip = str(hosts[0])
        
        print(f"Creating network for {tenant_name}: {subnet_cidr} (VXLAN: {vxlan_id})")
        
        # 1. Create logical switch
        self._run(["ovn-nbctl", "ls-add", switch_name])
        self._run(["ovn-nbctl", "set", "logical_switch", switch_name, 
                   f"other_config:vxlan={vxlan_id}"])
        
        # 2. Create DHCP options
        dhcp_uuid = self._run(["ovn-nbctl", "dhcp-options-create", subnet_cidr])
        
        # 3. Configure DHCP
        dhcp_mac = f"02:00:00:{vxlan_id:02x}:00:01"
        self._run(["ovn-nbctl", "dhcp-options-set-options", dhcp_uuid,
                   f"server_id={gateway_ip}",
                   f"server_mac={dhcp_mac}",
                   f"router={gateway_ip}",
                   "lease_time=86400",
                   "mtu=1400"])
        
        # 4. Attach DHCP to switch
        self._run(["ovn-nbctl", "set", "logical_switch", switch_name,
                   f"other_config:dhcp_options={dhcp_uuid}"])
        
        # 5. Connect to shared router
        router_port = f"lrp-{tenant_name}"
        router_mac = f"02:00:00:{vxlan_id:02x}:00:02"
        
        self._run(["ovn-nbctl", "lrp-add", self.router, router_port,
                   router_mac, f"{gateway_ip}/{network.prefixlen}"])
        
        switch_port = f"lsp-{tenant_name}-router"
        self._run(["ovn-nbctl", "lsp-add", switch_name, switch_port])
        self._run(["ovn-nbctl", "lsp-set-type", switch_port, "router"])
        self._run(["ovn-nbctl", "lsp-set-addresses", switch_port, "router"])
        self._run(["ovn-nbctl", "lsp-set-options", switch_port,
                   f"router-port={router_port}"])
        
        # 6. Add SNAT for internet access
        self._run(["ovn-nbctl", "lr-nat-add", self.router, "snat",
                   "192.168.100.1", subnet_cidr])
        
        return {
            "switch_name": switch_name,
            "subnet": subnet_cidr,
            "gateway": gateway_ip,
            "vxlan_id": vxlan_id,
            "dhcp_uuid": dhcp_uuid
        }
    
    def create_vm_port(self, tenant_name: str, vm_name: str, 
                       private_ip: str) -> Dict:
        """Create port for VM with specific IP"""
        
        switch_name = f"tenant-{tenant_name}"
        port_name = f"port-{vm_name}"
        
        # Generate MAC
        mac = f"02:00:00:{random.randint(0,255):02x}:{random.randint(0,255):02x}:{random.randint(0,255):02x}"
        
        # Create port
        self._run(["ovn-nbctl", "lsp-add", switch_name, port_name])
        
        # Set static IP
        self._run(["ovn-nbctl", "lsp-set-addresses", port_name, f"{mac} {private_ip}"])
        self._run(["ovn-nbctl", "lsp-set-port-security", port_name, f"{mac} {private_ip}"])
        
        # Get port UUID
        port_uuid = self._run(["ovn-nbctl", "get", "logical_switch_port",
                               port_name, "_uuid"])
        
        return {
            "port_name": port_name,
            "port_uuid": port_uuid,
            "mac_address": mac,
            "private_ip": private_ip
        }
    
    def assign_floating_ip(self, tenant_name: str, vm_name: str,
                           floating_ip: str, private_ip: str) -> Dict:
        """Assign floating IP to VM"""
        
        port_name = f"port-{vm_name}"
        nat_mac = f"02:00:00:00:{random.randint(0,255):02x}:{random.randint(0,255):02x}"
        
        # Create DNAT+SNAT rule
        self._run(["ovn-nbctl", "lr-nat-add", self.router, "dnat_and_snat",
                   floating_ip, private_ip, port_name, nat_mac])
        
        return {
            "floating_ip": floating_ip,
            "private_ip": private_ip,
            "vm_name": vm_name
        }
