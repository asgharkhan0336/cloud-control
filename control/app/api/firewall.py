"""Firewall / Security Groups - Users manage their own firewall rules"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.services.firewall_service import FirewallService

router = APIRouter(prefix="/api/v1/firewall", tags=["Firewall"])

# ============================================
# Enums and Models
# ============================================

class ProtocolEnum(str, Enum):
    tcp = "tcp"
    udp = "udp"
    icmp = "icmp"
    all = "all"

class RuleDirection(str, Enum):
    ingress = "ingress"
    egress = "egress"

class FirewallRuleCreate(BaseModel):
    direction: RuleDirection
    protocol: ProtocolEnum
    port_range: Optional[str] = Field(None, description="e.g., '80' or '8000-9000'")
    source_ip: Optional[str] = Field("0.0.0.0/0", description="CIDR or IP")
    description: Optional[str] = None

class FirewallRuleResponse(BaseModel):
    id: int
    direction: str
    protocol: str
    port_range: Optional[str]
    source_ip: str
    description: Optional[str]
    priority: int
    enabled: bool

class SecurityGroupCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

class SecurityGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    vm_count: int
    rule_count: int
    created_at: str
    
    class Config:
        from_attributes = True

class SecurityGroupRuleResponse(BaseModel):
    id: int
    security_group_id: int
    direction: str
    protocol: str
    port_min: Optional[int]
    port_max: Optional[int]
    source_ip: str
    description: Optional[str]
    priority: int
    enabled: bool

# ============================================
# Security Group Endpoints
# ============================================

@router.post("/groups", response_model=SecurityGroupResponse)
async def create_security_group(
    group_data: SecurityGroupCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new security group (firewall)
    Users can create multiple groups for different purposes
    """
    try:
        service = FirewallService(db)
        group = service.create_security_group(
            user_id=current_user.id,
            name=group_data.name,
            description=group_data.description
        )
        return group
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/groups", response_model=List[SecurityGroupResponse])
async def list_security_groups(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all security groups for the current user"""
    service = FirewallService(db)
    return service.list_user_security_groups(current_user.id)

@router.get("/groups/{group_id}", response_model=SecurityGroupResponse)
async def get_security_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a security group"""
    service = FirewallService(db)
    group = service.get_security_group(group_id, current_user.id)
    if not group:
        raise HTTPException(status_code=404, detail="Security group not found")
    return group

@router.delete("/groups/{group_id}")
async def delete_security_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a security group"""
    try:
        service = FirewallService(db)
        return service.delete_security_group(group_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Firewall Rules Endpoints
# ============================================

@router.post("/groups/{group_id}/rules", response_model=SecurityGroupRuleResponse)
async def add_firewall_rule(
    group_id: int,
    rule_data: FirewallRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a firewall rule to a security group
    Common rules:
    - SSH: tcp, port 22, source 0.0.0.0/0 (or specific IP)
    - HTTP: tcp, port 80, source 0.0.0.0/0
    - HTTPS: tcp, port 443, source 0.0.0.0/0
    - MySQL: tcp, port 3306, source 10.0.0.0/24 (internal only)
    """
    try:
        service = FirewallService(db)
        rule = service.add_rule(
            group_id=group_id,
            user_id=current_user.id,
            direction=rule_data.direction,
            protocol=rule_data.protocol,
            port_range=rule_data.port_range,
            source_ip=rule_data.source_ip,
            description=rule_data.description
        )
        return rule
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/groups/{group_id}/rules", response_model=List[SecurityGroupRuleResponse])
async def list_firewall_rules(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all rules in a security group"""
    service = FirewallService(db)
    return service.list_rules(group_id, current_user.id)

@router.delete("/rules/{rule_id}")
async def delete_firewall_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a firewall rule"""
    try:
        service = FirewallService(db)
        return service.delete_rule(rule_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/rules/{rule_id}/toggle")
async def toggle_firewall_rule(
    rule_id: int,
    enabled: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable or disable a firewall rule"""
    try:
        service = FirewallService(db)
        return service.toggle_rule(rule_id, current_user.id, enabled)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# VM Assignment Endpoints
# ============================================

@router.post("/groups/{group_id}/assign/{vm_name}")
async def assign_security_group_to_vm(
    group_id: int,
    vm_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Assign a security group to a VM
    One VM can have multiple security groups
    """
    try:
        service = FirewallService(db)
        return service.assign_to_vm(group_id, vm_name, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/groups/{group_id}/unassign/{vm_name}")
async def unassign_security_group_from_vm(
    group_id: int,
    vm_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a security group from a VM"""
    try:
        service = FirewallService(db)
        return service.unassign_from_vm(group_id, vm_name, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Quick Templates
# ============================================

@router.post("/templates/web-server")
async def apply_web_server_template(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Apply web server firewall template
    Allows: SSH (22), HTTP (80), HTTPS (443)
    """
    try:
        service = FirewallService(db)
        return service.apply_template_web_server(group_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/database")
async def apply_database_template(
    group_id: int,
    vpc_cidr: str = "10.0.0.0/24",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Apply database firewall template
    Allows: MySQL (3306) and PostgreSQL (5432) from VPC only
    """
    try:
        service = FirewallService(db)
        return service.apply_template_database(group_id, current_user.id, vpc_cidr)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))