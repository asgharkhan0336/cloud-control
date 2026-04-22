from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import re

class VMState(str, Enum):
    RUNNING = "running"
    SHUTOFF = "shutoff"
    PAUSED = "paused"
    CRASHED = "crashed"
    NOSTATE = "nostate"
    UNKNOWN = "unknown"

class VMCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    memory: int = Field(1024, ge=512, le=131072, description="Memory in MB")
    vcpus: int = Field(1, ge=1, le=32)
    disk_size: int = Field(10, ge=5, le=1000, description="Disk size in GB")
    os_variant: str = Field("ubuntu24.04", description="OS type for virt-install")
    network_bridge: str = Field("virbr0")
    
    # Network configuration
    vpc_id: Optional[int] = Field(None, description="VPC ID to attach VM")
    subnet_id: Optional[int] = Field(None, description="Subnet ID within VPC")
    private_ip: Optional[str] = Field(None, description="Request specific private IP")
    
    # Security
    security_group_ids: Optional[List[int]] = Field(None, description="Security groups to attach")
    ssh_key_ids: Optional[List[int]] = Field(None, description="SSH keys for authentication")
    
    # Cloud-init
    ssh_key: Optional[str] = Field(None, description="SSH public key for cloud-init")
    user_data: Optional[str] = Field(None, description="Cloud-init user data")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v in ['all', 'host', 'create', 'delete']:
            raise ValueError(f"'{v}' is a reserved name")
        return v

class VMSecurityGroupInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class VMResponse(BaseModel):
    # Database fields
    id: Optional[int] = None
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    # Basic info
    name: str
    state: VMState
    memory: int
    vcpus: int
    disk_size: Optional[int] = None
    os_variant: Optional[str] = None
    
    # Performance metrics
    cpu_time: int = 0
    cpu_percent: float = 0.0
    disk_usage: Dict[str, int] = {}
    
    # Network
    ip_addresses: List[str] = []
    private_ip: Optional[str] = None
    floating_ip: Optional[str] = None
    network_name: Optional[str] = None
    
    # VPC and Subnet
    vpc_id: Optional[int] = None
    vpc_name: Optional[str] = None
    vpc_cidr: Optional[str] = None
    subnet_id: Optional[int] = None
    subnet_name: Optional[str] = None
    subnet_cidr: Optional[str] = None
    
    # Security
    security_groups: List[VMSecurityGroupInfo] = []
    
    class Config:
        from_attributes = True

class VMListResponse(BaseModel):
    vms: List[VMResponse]
    total: int
    running: int
    stopped: int

class VMUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    memory: Optional[int] = Field(None, ge=512, le=131072)
    vcpus: Optional[int] = Field(None, ge=1, le=32)
    disk_size: Optional[int] = Field(None, ge=5, le=1000)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v and v in ['all', 'host', 'create', 'delete']:
            raise ValueError(f"'{v}' is a reserved name")
        return v

class VMResizeRequest(BaseModel):
    memory: Optional[int] = Field(None, ge=512, le=131072)
    vcpus: Optional[int] = Field(None, ge=1, le=32)
    disk_size: Optional[int] = Field(None, ge=5, le=1000)

class VMAttachNetworkRequest(BaseModel):
    vpc_id: int
    subnet_id: Optional[int] = None
    private_ip: Optional[str] = None

class VMAttachSecurityGroupRequest(BaseModel):
    security_group_ids: List[int]

class VMAssignFloatingIPRequest(BaseModel):
    floating_ip: Optional[str] = None
    subnet_id: Optional[int] = None

class VMConsoleResponse(BaseModel):
    url: str
    type: str  # 'vnc' or 'spice'
    password: Optional[str] = None

class VMMetricsResponse(BaseModel):
    cpu: List[Dict[str, Any]]  # [{time: string, value: float}]
    memory: List[Dict[str, Any]]
    network: List[Dict[str, Any]]
    disk: List[Dict[str, Any]]

class HostInfoResponse(BaseModel):
    hostname: str
    model: str
    memory_total: int
    memory_free: int
    cpu_cores: int
    cpu_threads: int
    cpu_model: str
    kvm_version: str
    libvirt_version: str
    storage_pools: List[Dict[str, Any]]
    networks: List[Dict[str, Any]]

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None