import libvirt
import psutil
import os
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
import xml.etree.ElementTree as ET
from jinja2 import Template

from app.config import settings
from app.models.vm import VMState, VMResponse

class LibvirtService:
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establish connection to libvirt"""
        try:
            self.conn = libvirt.open(settings.libvirt_uri)
            if not self.conn:
                raise Exception("Failed to open connection to libvirt")
        except libvirt.libvirtError as e:
            raise Exception(f"Failed to connect to libvirt: {e}")
    
    def _ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            if self.conn:
                # Test connection
                self.conn.getVersion()
            else:
                self._connect()
        except:
            self._connect()
    
    def close(self):
        """Close libvirt connection"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def get_host_info(self) -> Dict[str, Any]:
        """Get host system information"""
        self._ensure_connection()
        hostname = self.conn.getHostname()
        info = self.conn.getInfo()
        
        libvirt_version = f"{self.conn.getLibVersion() // 1000000}." \
                         f"{(self.conn.getLibVersion() % 1000000) // 1000}." \
                         f"{self.conn.getLibVersion() % 1000}"
        
        storage_pools = []
        for pool in self.conn.listAllStoragePools():
            pool_info = pool.info()
            storage_pools.append({
                "name": pool.name(),
                "state": pool_info[0],
                "capacity": pool_info[1],
                "allocation": pool_info[2],
                "available": pool_info[3]
            })
        
        networks = []
        for net in self.conn.listAllNetworks():
            net_info = net.XMLDesc()
            networks.append({
                "name": net.name(),
                "active": net.isActive(),
                "bridge": self._get_bridge_from_xml(net_info)
            })
        
        return {
            "hostname": hostname,
            "model": info[0],
            "memory_total": info[1] * 1024,
            "memory_free": psutil.virtual_memory().available // (1024 * 1024),
            "cpu_cores": info[2],
            "cpu_threads": info[2] * info[3] if len(info) > 3 else info[2],
            "cpu_model": info[4] if len(info) > 4 else "Unknown",
            "kvm_version": self._get_kvm_version(),
            "libvirt_version": libvirt_version,
            "storage_pools": storage_pools,
            "networks": networks
        }
    
    def _get_kvm_version(self) -> str:
        """Get KVM version"""
        try:
            result = subprocess.run(['kvm', '--version'], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "Unknown"
    
    def _get_bridge_from_xml(self, xml_desc: str) -> str:
        """Extract bridge name from network XML"""
        try:
            root = ET.fromstring(xml_desc)
            bridge = root.find('.//bridge')
            return bridge.get('name') if bridge is not None else "unknown"
        except:
            return "unknown"
    
    def list_vms(self) -> List[Dict[str, Any]]:
        """List all VMs with detailed information"""
        self._ensure_connection()
        vms = []
        for domain in self.conn.listAllDomains():
            vm_info = self._get_domain_info(domain)
            vms.append(vm_info)
        return vms
    
    def get_vm(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific VM information"""
        self._ensure_connection()
        try:
            domain = self.conn.lookupByName(name)
            return self._get_domain_info(domain)
        except libvirt.libvirtError:
            return None
    
    def _get_domain_info(self, domain) -> Dict[str, Any]:
        """Get detailed domain information"""
        name = domain.name()
        state, max_mem, memory, vcpus, cpu_time = domain.info()
        
        state_map = {
            libvirt.VIR_DOMAIN_RUNNING: VMState.RUNNING,
            libvirt.VIR_DOMAIN_SHUTOFF: VMState.SHUTOFF,
            libvirt.VIR_DOMAIN_PAUSED: VMState.PAUSED,
            libvirt.VIR_DOMAIN_CRASHED: VMState.CRASHED,
            libvirt.VIR_DOMAIN_NOSTATE: VMState.NOSTATE,
        }
        
        cpu_percent = 0.0
        try:
            cpu_stats = domain.getCPUStats(True)
            if cpu_stats:
                cpu_percent = (cpu_stats[0]['cpu_time'] / 1000000000)
        except:
            pass
        
        ip_addresses = []
        try:
            interfaces = domain.interfaceAddresses(
                libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE
            )
            for iface in interfaces.values():
                if 'addrs' in iface:
                    for addr in iface['addrs']:
                        if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                            ip_addresses.append(addr['addr'])
        except:
            try:
                interfaces = domain.interfaceAddresses(
                    libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP
                )
                for iface in interfaces.values():
                    if 'addrs' in iface:
                        for addr in iface['addrs']:
                            if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                ip_addresses.append(addr['addr'])
            except:
                pass
        
        return {
            "name": name,
            "state": state_map.get(state, VMState.NOSTATE),
            "memory": memory // 1024,
            "vcpus": vcpus,
            "cpu_time": cpu_time,
            "cpu_percent": cpu_percent,
            "ip_addresses": ip_addresses,
            "disk_usage": self._get_disk_usage(domain)
        }
    
    def _get_disk_usage(self, domain) -> Dict[str, int]:
        """Get disk usage information"""
        disk_usage = {}
        try:
            xml_desc = domain.XMLDesc()
            root = ET.fromstring(xml_desc)
            for disk in root.findall('.//disk[@device="disk"]'):
                source = disk.find('source')
                if source is not None:
                    file_path = source.get('file')
                    if file_path and os.path.exists(file_path):
                        stat = os.stat(file_path)
                        disk_usage[file_path] = stat.st_size // (1024 * 1024 * 1024)
        except:
            pass
        return disk_usage
    
    def create_vm(self, name: str, memory: int, vcpus: int, 
                  disk_size: int, os_variant: str = "ubuntu24.04",
                  network_bridge: str = "virbr0") -> bool:
        """Create a new VM using virt-install"""
        try:
            self._ensure_connection()
            try:
                self.conn.lookupByName(name)
                raise Exception(f"VM '{name}' already exists")
            except libvirt.libvirtError:
                pass
            
            disk_path = f"{settings.vm_images_path}/{name}.qcow2"
            
            # Check if base image exists
            base_image = f"{settings.base_images_path}/{os_variant}.qcow2"
            if os.path.exists(base_image):
                subprocess.run(['cp', base_image, disk_path], check=True)
                subprocess.run(['qemu-img', 'resize', disk_path, f"{disk_size}G"], check=True)
            else:
                subprocess.run([
                    'qemu-img', 'create', '-f', 'qcow2',
                    disk_path, f"{disk_size}G"
                ], check=True)
            
            cmd = [
                'virt-install',
                '--connect', 'qemu:///system',
                '--name', name,
                '--memory', str(memory),
                '--vcpus', str(vcpus),
                '--disk', f"path={disk_path},format=qcow2,bus=virtio",
                '--network', f"bridge={network_bridge},model=virtio",
                '--graphics', 'none',
                '--os-variant', os_variant,
                '--import',
                '--noautoconsole'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"virt-install failed: {result.stderr}")
            
            return True
            
        except Exception as e:
            disk_path = f"{settings.vm_images_path}/{name}.qcow2"
            if os.path.exists(disk_path):
                os.remove(disk_path)
            raise e
    
    def start_vm(self, name: str) -> bool:
        """Start a VM"""
        self._ensure_connection()
        try:
            domain = self.conn.lookupByName(name)
            if domain.isActive():
                return True
            domain.create()
            return True
        except libvirt.libvirtError as e:
            raise Exception(f"Failed to start VM: {e}")
    
    def stop_vm(self, name: str, force: bool = False) -> bool:
        """Stop a VM"""
        self._ensure_connection()
        try:
            domain = self.conn.lookupByName(name)
            if not domain.isActive():
                return True
            if force:
                domain.destroy()
            else:
                domain.shutdown()
            return True
        except libvirt.libvirtError as e:
            raise Exception(f"Failed to stop VM: {e}")
    
    def delete_vm(self, name: str) -> bool:
        """Delete a VM and its disk"""
        self._ensure_connection()
        try:
            domain = self.conn.lookupByName(name)
            
            if domain.isActive():
                domain.destroy()
            
            xml_desc = domain.XMLDesc()
            root = ET.fromstring(xml_desc)
            disk_paths = []
            for disk in root.findall('.//disk[@device="disk"]'):
                source = disk.find('source')
                if source is not None:
                    file_path = source.get('file')
                    if file_path:
                        disk_paths.append(file_path)
            
            domain.undefine()
            
            for disk_path in disk_paths:
                if os.path.exists(disk_path):
                    os.remove(disk_path)
            
            return True
        except libvirt.libvirtError as e:
            raise Exception(f"Failed to delete VM: {e}")

def reboot_vm(self, name: str) -> bool:
    """Reboot a VM"""
    try:
        domain = self.conn.lookupByName(name)
        domain.reboot()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to reboot VM: {e}")

def pause_vm(self, name: str) -> bool:
    """Pause a VM"""
    try:
        domain = self.conn.lookupByName(name)
        domain.suspend()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to pause VM: {e}")

def resume_vm(self, name: str) -> bool:
    """Resume a paused VM"""
    try:
        domain = self.conn.lookupByName(name)
        domain.resume()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to resume VM: {e}")

def get_console_url(self, name: str) -> Dict[str, Any]:
    """Get VNC/SPICE console URL"""
    try:
        domain = self.conn.lookupByName(name)
        xml_desc = domain.XMLDesc()
        root = ET.fromstring(xml_desc)
        
        graphics = root.find('.//graphics')
        if graphics is not None:
            return {
                'type': graphics.get('type', 'vnc'),
                'port': graphics.get('port'),
                'listen': graphics.get('listen', '0.0.0.0'),
                'password': graphics.get('passwd')
            }
        return {'type': 'none', 'url': None}
    except:
        return {'type': 'none', 'url': None}