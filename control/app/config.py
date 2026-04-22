from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    api_title: str = "Cloud Platform API"
    api_version: str = "1.0.0"
    api_description: str = "KVM-based cloud platform REST API"
    
    # Libvirt Settings
    libvirt_uri: str = "qemu:///system"
    
    # Storage Paths
    vm_images_path: str = "/var/lib/libvirt/images"
    vm_templates_path: str = "./templates"
    base_images_path: str = "./images"
    
    # VM Defaults
    default_vm_memory: int = 1024  # MB
    default_vm_vcpus: int = 1
    default_vm_disk_size: int = 10  # GB
    default_network_bridge: str = "virbr0"
    
    # Network Settings
    vm_ip_pool_start: str = "192.168.122.100"
    vm_ip_pool_end: str = "192.168.122.200"
    console_host:str = "49.12.132.53:8000"
    class Config:
        env_file = ".env"

settings = Settings()
