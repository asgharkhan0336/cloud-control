"""Firewall Service - Manages security groups and ACLs"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import SecurityGroup, FirewallRule, VM

class FirewallService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_security_group(self, user_id: int, name: str, description: str = None) -> Dict:
        """Create a new security group"""
        
        # Check if name already exists for this user
        existing = self.db.query(SecurityGroup).filter(
            SecurityGroup.owner_id == user_id,
            SecurityGroup.name == name
        ).first()
        
        if existing:
            raise ValueError(f"Security group '{name}' already exists")
        
        group = SecurityGroup(
            name=name,
            description=description,
            owner_id=user_id
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        
        return self._format_group(group)
    
    def add_rule(self, group_id: int, user_id: int, direction: str, 
                 protocol: str, port_range: str = None, 
                 source_ip: str = "0.0.0.0/0", description: str = None) -> Dict:
        """Add a firewall rule to security group"""
        
        # Verify ownership
        group = self._verify_group_ownership(group_id, user_id)
        
        # Parse port range
        port_min, port_max = None, None
        if port_range and protocol in ['tcp', 'udp']:
            if '-' in port_range:
                port_min, port_max = map(int, port_range.split('-'))
            else:
                port_min = port_max = int(port_range)
        
        # Get next priority
        max_priority = self.db.query(FirewallRule).filter(
            FirewallRule.security_group_id == group_id
        ).count()
        
        rule = FirewallRule(
            security_group_id=group_id,
            direction=direction,
            protocol=protocol,
            port_min=port_min,
            port_max=port_max,
            source_ip=source_ip,
            description=description,
            priority=max_priority + 100
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        # Apply rule to OVN ACLs for all VMs in this group
        self._sync_ovn_acls(group_id)
        
        return self._format_rule(rule)
    
    def _sync_ovn_acls(self, group_id: int):
        """Sync firewall rules to OVN ACLs"""
        group = self.db.query(SecurityGroup).get(group_id)
        if not group:
            return
        
        # Get all VMs in this security group
        vms = group.vms
        
        for vm in vms:
            if not vm.private_ip:
                continue
            
            # Get VPC switch name
            vpc_switch = f"vpc-{vm.owner.username}"
            
            # Apply each rule as OVN ACL
            for rule in group.rules:
                if not rule.enabled:
                    continue
                
                self._apply_ovn_acl(vpc_switch, vm.private_ip, rule)
    
    def _apply_ovn_acl(self, switch: str, vm_ip: str, rule: FirewallRule):
        """Apply a single firewall rule as OVN ACL"""
        import subprocess
        
        # Build ACL match string
        match = f"ip4.dst == {vm_ip}"
        
        if rule.protocol != 'all':
            match += f" && {rule.protocol}"
        
        if rule.port_min:
            if rule.port_min == rule.port_max:
                match += f" && {rule.protocol}.dst == {rule.port_min}"
            else:
                match += f" && {rule.port_min} <= {rule.protocol}.dst <= {rule.port_max}"
        
        if rule.source_ip != "0.0.0.0/0":
            match += f" && ip4.src == {rule.source_ip}"
        
        # Determine action
        action = "allow-related" if rule.direction == "ingress" else "allow"
        
        # Add ACL to OVN
        acl_name = f"acl-{rule.security_group_id}-{rule.id}"
        
        cmd = [
            "ovn-nbctl", "acl-add", switch,
            "to-lport" if rule.direction == "ingress" else "from-lport",
            str(rule.priority),
            match,
            action
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except:
            pass  # ACL might already exist
    
    def apply_template_web_server(self, group_id: int, user_id: int) -> Dict:
        """Apply web server template rules"""
        
        rules = [
            {"direction": "ingress", "protocol": "tcp", "port_range": "22", 
             "source_ip": "0.0.0.0/0", "description": "SSH"},
            {"direction": "ingress", "protocol": "tcp", "port_range": "80", 
             "source_ip": "0.0.0.0/0", "description": "HTTP"},
            {"direction": "ingress", "protocol": "tcp", "port_range": "443", 
             "source_ip": "0.0.0.0/0", "description": "HTTPS"},
            {"direction": "egress", "protocol": "all", "port_range": None, 
             "source_ip": "0.0.0.0/0", "description": "Allow all outbound"},
        ]
        
        added = []
        for rule_data in rules:
            rule = self.add_rule(group_id, user_id, **rule_data)
            added.append(rule)
        
        return {"template": "web-server", "rules_added": len(added)}
    
    def _verify_group_ownership(self, group_id: int, user_id: int) -> SecurityGroup:
        """Verify user owns the security group"""
        group = self.db.query(SecurityGroup).get(group_id)
        if not group:
            raise ValueError("Security group not found")
        if group.owner_id != user_id:
            raise ValueError("Permission denied")
        return group
    
    def _format_group(self, group: SecurityGroup) -> Dict:
        """Format security group for response"""
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "is_default": group.is_default,
            "vm_count": len(group.vms),
            "rule_count": len(group.rules),
            "created_at": group.created_at.isoformat() if group.created_at else None
        }
    
    def _format_rule(self, rule: FirewallRule) -> Dict:
        """Format firewall rule for response"""
        port_range = None
        if rule.port_min:
            port_range = str(rule.port_min) if rule.port_min == rule.port_max else f"{rule.port_min}-{rule.port_max}"
        
        return {
            "id": rule.id,
            "security_group_id": rule.security_group_id,
            "direction": rule.direction,
            "protocol": rule.protocol,
            "port_min": rule.port_min,
            "port_max": rule.port_max,
            "port_range": port_range,
            "source_ip": rule.source_ip,
            "description": rule.description,
            "priority": rule.priority,
            "enabled": rule.enabled
        }