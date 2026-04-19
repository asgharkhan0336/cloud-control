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

class VMCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9-]+$")
    memory: int = Field(1024, ge=512, le=131072, description="Memory in MB")
    vcpus: int = Field(1, ge=1, le=32)
    disk_size: int = Field(10, ge=5, le=1000, description="Disk size in GB")
    os_variant: str = Field("ubuntu22.04", description="OS type for virt-install")
    network_bridge: str = Field("virbr0")
    ssh_key: Optional[str] = Field(None, description="SSH public key for cloud-init")
    user_data: Optional[str] = Field(None, description="Cloud-init user data")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v in ['all', 'host', 'create', 'delete']:
            raise ValueError(f"'{v}' is a reserved name")
        return v

class VMResponse(BaseModel):
    name: str
    state: VMState
    memory: int
    vcpus: int
    cpu_time: int = 0
    cpu_percent: float = 0.0
    ip_addresses: List[str] = []
    disk_usage: Dict[str, int] = {}
    created_at: Optional[datetime] = None
    
class VMListResponse(BaseModel):
    vms: List[VMResponse]
    total: int
    running: int
    stopped: int

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
