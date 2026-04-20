from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

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
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class VM(Base):
    __tablename__ = "vms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    memory = Column(Integer, nullable=False)
    vcpus = Column(Integer, nullable=False)
    disk_size = Column(Integer, nullable=False)
    os_variant = Column(String(50), nullable=False)
    status = Column(String(20), default="stopped")
    ip_address = Column(String(15))
    network_name = Column(String(50), default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="vms")

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
    
    # Relationships
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
    
    # Relationships
    user = relationship("User", back_populates="billing_records")

class Network(Base):
    __tablename__ = "networks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    cidr = Column(String(20), nullable=False)
    gateway = Column(String(15), nullable=False)
    vlan_id = Column(Integer, unique=True, nullable=True)
    vxlan_id = Column(Integer, unique=True, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="networks")
    floating_ips = relationship("FloatingIP", back_populates="network")

class FloatingIP(Base):
    __tablename__ = "floating_ips"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(15), unique=True, nullable=False)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"))
    vm_name = Column(String(50), ForeignKey("vms.name", ondelete="SET NULL"), nullable=True)
    is_allocated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    network = relationship("Network", back_populates="floating_ips")

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
    
    # Relationships
    user = relationship("User", back_populates="ssh_keys")