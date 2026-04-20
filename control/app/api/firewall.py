"""Firewall API - Security Groups & Rules"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from app.database import get_db
from app.auth.auth import get_current_active_user
from app.models.database import User
from app.services.firewall_service import FirewallService

router = APIRouter(prefix="/api/v1/firewall", tags=["Firewall"])

# ============================================
# Enums
# ============================================

class ProtocolEnum(str, Enum):
    tcp = "tcp"
    udp = "udp"
    icmp = "icmp"
    all = "all"

class RuleDirection(str, Enum):
    ingress = "ingress"
    egress = "egress"

# ============================================
# Pydantic Models
# ============================================

class SecurityGroupCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9-_ ]+$")
    description: Optional[str] = Field(None, max_length=255)

class SecurityGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    vm_count: int
    rule_count: int
    created_at: Optional[str]

class FirewallRuleCreate(BaseModel):
    direction: RuleDirection
    protocol: ProtocolEnum
    port_range: Optional[str] = Field(None, description="e.g., '80' or '8000-9000'")
    source_ip: str = Field("0.0.0.0/0", description="CIDR or IP address")
    description: Optional[str] = None

class FirewallRuleUpdate(BaseModel):
    direction: Optional[RuleDirection] = None
    protocol: Optional[ProtocolEnum] = None
    port_range: Optional[str] = None
    source_ip: Optional[str] = None
    description: Optional[str] = None

class FirewallRuleResponse(BaseModel):
    id: int
    security_group_id: int
    direction: str
    protocol: str
    port_min: Optional[int]
    port_max: Optional[int]
    port_range: Optional[str]
    source_ip: str
    description: Optional[str]
    priority: int
    enabled: bool
    created_at: Optional[str]

# ============================================
# Security Group Endpoints
# ============================================

@router.post("/groups", response_model=SecurityGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_security_group(
    group_data: SecurityGroupCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new security group"""
    try:
        service = FirewallService(db)
        return service.create_security_group(
            user_id=current_user.id,
            name=group_data.name,
            description=group_data.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/groups", response_model=List[SecurityGroupResponse])
async def list_security_groups(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all security groups"""
    service = FirewallService(db)
    return service.list_user_security_groups(current_user.id)

@router.get("/groups/{group_id}", response_model=SecurityGroupResponse)
async def get_security_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get security group details"""
    service = FirewallService(db)
    sg = service.get_security_group(group_id, current_user.id)
    if not sg:
        raise HTTPException(status_code=404, detail="Security group not found")
    return sg

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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Firewall Rule Endpoints
# ============================================

@router.post("/groups/{group_id}/rules", response_model=FirewallRuleResponse)
async def add_firewall_rule(
    group_id: int,
    rule_data: FirewallRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a firewall rule to a security group"""
    try:
        service = FirewallService(db)
        return service.add_rule(
            group_id=group_id,
            user_id=current_user.id,
            direction=rule_data.direction.value,
            protocol=rule_data.protocol.value,
            port_range=rule_data.port_range,
            source_ip=rule_data.source_ip,
            description=rule_data.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/groups/{group_id}/rules", response_model=List[FirewallRuleResponse])
async def list_firewall_rules(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all rules in a security group"""
    try:
        service = FirewallService(db)
        return service.list_rules(group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rules/{rule_id}", response_model=FirewallRuleResponse)
async def get_firewall_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific firewall rule"""
    service = FirewallService(db)
    rule = service.get_rule(rule_id, current_user.id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.patch("/rules/{rule_id}", response_model=FirewallRuleResponse)
async def update_firewall_rule(
    rule_id: int,
    rule_update: FirewallRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a firewall rule"""
    try:
        service = FirewallService(db)
        return service.update_rule(
            rule_id=rule_id,
            user_id=current_user.id,
            direction=rule_update.direction.value if rule_update.direction else None,
            protocol=rule_update.protocol.value if rule_update.protocol else None,
            port_range=rule_update.port_range,
            source_ip=rule_update.source_ip,
            description=rule_update.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/rules/{rule_id}/toggle", response_model=FirewallRuleResponse)
async def toggle_firewall_rule(
    rule_id: int,
    enabled: bool = Query(..., description="Enable or disable the rule"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable or disable a firewall rule"""
    try:
        service = FirewallService(db)
        return service.toggle_rule(rule_id, current_user.id, enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# VM Assignment Endpoints
# ============================================

@router.post("/groups/{group_id}/assign")
async def assign_security_group(
    group_id: int,
    vm_name: str = Query(..., description="VM name"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign security group to a VM"""
    try:
        service = FirewallService(db)
        return service.assign_to_vm(group_id, vm_name, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/groups/{group_id}/unassign")
async def unassign_security_group(
    group_id: int,
    vm_name: str = Query(..., description="VM name"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove security group from a VM"""
    try:
        service = FirewallService(db)
        return service.unassign_from_vm(group_id, vm_name, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/vms/{vm_name}/groups", response_model=List[SecurityGroupResponse])
async def list_vm_security_groups(
    vm_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List security groups assigned to a VM"""
    try:
        service = FirewallService(db)
        return service.list_vm_security_groups(vm_name, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Template Endpoints
# ============================================

@router.post("/groups/{group_id}/templates/web-server")
async def apply_web_server_template(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Apply web server firewall template"""
    try:
        service = FirewallService(db)
        return service.apply_template_web_server(group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/groups/{group_id}/templates/database")
async def apply_database_template(
    group_id: int,
    vpc_cidr: str = Query("10.0.0.0/24", description="VPC CIDR for internal access"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Apply database firewall template (internal access only)"""
    try:
        service = FirewallService(db)
        return service.apply_template_database(group_id, current_user.id, vpc_cidr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/groups/{group_id}/templates/strict")
async def apply_strict_template(
    group_id: int,
    allowed_ips: List[str] = Query(..., description="List of allowed IP addresses"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Apply strict firewall template (only allow specific IPs)"""
    try:
        service = FirewallService(db)
        return service.apply_template_strict(group_id, current_user.id, allowed_ips)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))