"""Database Models for Cloud Platform"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, 
    ForeignKey, DECIMAL, Text, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# ============================================
# User and Authentication Models
# ============================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    vms = relationship("VM", back_populates="owner", cascade="all, delete-orphan")
    quota = relationship("ResourceQuota", back_populates="user", uselist=False, cascade="all, delete-orphan")
    billing_records = relationship("BillingRecord", back_populates="user", cascade="all, delete-orphan")
    networks = relationship("Network", back_populates="owner", cascade="all, delete-orphan")
    security_groups = relationship("SecurityGroup", back_populates="owner", cascade="all, delete-orphan")
    ssh_keys = relationship("SSHKey", back_populates="user", cascade="all, delete-orphan")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    key_name = Column(String(100), nullable=False)
    api_key_hash = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="api_keys")

class ResourceQuota(Base):
    __tablename__ = "resource_quotas"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    max_vms = Column(Integer, default=10)
    max_memory_mb = Column(Integer, default=8192)
    max_vcpus = Column(Integer, default=8)
    max_disk_gb = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="quota")

class BillingRecord(Base):
    __tablename__ = "billing_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    vm_name = Column(String(50), nullable=False)
    usage_minutes = Column(Integer, nullable=False)
    cost = Column(DECIMAL(10, 4), nullable=False)
    rate_per_hour = Column(DECIMAL(10, 4), nullable=False)
    billed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="billing_records")

class SSHKey(Base):
    __tablename__ = "ssh_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(50), nullable=False)
    public_key = Column(Text, nullable=False)
    fingerprint = Column(String(255), nullable=False)
    key_type = Column(String(50))
    key_bits = Column(Integer)
    key_comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="ssh_keys")
    
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_ssh_key_user_name'),)

# ============================================
# VM Model
# ============================================

class VM(Base):
    __tablename__ = "vms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    vpc_id = Column(Integer, ForeignKey("networks.id"), nullable=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=True)
    memory = Column(Integer, nullable=False)
    vcpus = Column(Integer, nullable=False)
    disk_size = Column(Integer, nullable=False)
    os_variant = Column(String(50), nullable=False)
    status = Column(String(20), default="stopped")
    private_ip = Column(String(15))
    floating_ip = Column(String(15))
    network_name = Column(String(50), default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    owner = relationship("User", back_populates="vms")
    vpc = relationship("Network", foreign_keys=[vpc_id], back_populates="vms")
    subnet = relationship("Subnet", foreign_keys=[subnet_id], back_populates="vms")
    security_groups = relationship("SecurityGroup", secondary="vm_security_groups", back_populates="vms")
    floating_ip = relationship("FloatingIP", foreign_keys="FloatingIP.vm_id", back_populates="vm", uselist=False)

# ============================================
# VPC and Networking Models
# ============================================

class Network(Base):
    __tablename__ = "networks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    cidr = Column(String(20), nullable=False)
    gateway = Column(String(15), nullable=False)
    vni = Column(Integer, unique=True, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="networks")
    subnets = relationship("Subnet", back_populates="vpc", cascade="all, delete-orphan")
    vms = relationship("VM", foreign_keys=[VM.vpc_id], back_populates="vpc")
    
    __table_args__ = (UniqueConstraint('owner_id', 'name', name='uq_network_owner_name'),)

class Subnet(Base):
    __tablename__ = "subnets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    vpc_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"))
    cidr = Column(String(20), nullable=False)
    gateway = Column(String(15), nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    vpc = relationship("Network", back_populates="subnets")
    vms = relationship("VM", foreign_keys=[VM.subnet_id], back_populates="subnet")
    floating_ips = relationship("FloatingIP", back_populates="subnet", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('vpc_id', 'name', name='uq_subnet_vpc_name'),)

# ============================================
# Security Group and Firewall Models
# ============================================

class SecurityGroup(Base):
    __tablename__ = "security_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="security_groups")
    rules = relationship("FirewallRule", back_populates="security_group", cascade="all, delete-orphan")
    vms = relationship("VM", secondary="vm_security_groups", back_populates="security_groups")
    
    __table_args__ = (UniqueConstraint('owner_id', 'name', name='uq_security_group_owner_name'),)

class FirewallRule(Base):
    __tablename__ = "firewall_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    security_group_id = Column(Integer, ForeignKey("security_groups.id", ondelete="CASCADE"))
    direction = Column(String(10), nullable=False)
    protocol = Column(String(10), nullable=False)
    port_min = Column(Integer, nullable=True)
    port_max = Column(Integer, nullable=True)
    source_ip = Column(String(20), default="0.0.0.0/0")
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=100)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    security_group = relationship("SecurityGroup", back_populates="rules")

class VMSecurityGroup(Base):
    __tablename__ = "vm_security_groups"
    
    vm_id = Column(Integer, ForeignKey("vms.id", ondelete="CASCADE"), primary_key=True)
    security_group_id = Column(Integer, ForeignKey("security_groups.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

# ============================================
# VPC Peering Model
# ============================================

class VPCPeering(Base):
    __tablename__ = "vpc_peerings"
    
    id = Column(Integer, primary_key=True, index=True)
    vpc_a_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"))
    vpc_b_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (UniqueConstraint('vpc_a_id', 'vpc_b_id', name='uq_vpc_peering'),)

    
class FloatingIP(Base):
    __tablename__ = "floating_ips"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(15), unique=True, nullable=False)
    subnet_id = Column(Integer, ForeignKey("subnets.id", ondelete="CASCADE"))
    vm_id = Column(Integer, ForeignKey("vms.id", ondelete="SET NULL"), nullable=True)
    is_allocated = Column(Boolean, default=False)
    allocated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subnet = relationship("Subnet", back_populates="floating_ips")
    vm = relationship("VM", foreign_keys=[vm_id], back_populates="floating_ip")