"""Firewall Service - Security Groups and Rules Management"""

import subprocess
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import SecurityGroup, FirewallRule, VM, User, VMSecurityGroup, Network

class FirewallService:
    def __init__(self, db: Session):
        self.db = db
    
    def _run_ovn(self, cmd: list) -> str:
        """Execute OVN command"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"OVN Error: {result.stderr}")
        return result.stdout.strip()
    
    # ============================================
    # Security Group Operations
    # ============================================
    
    def create_security_group(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None
    ) -> Dict:
        """Create a new security group"""
        
        existing = self.db.query(SecurityGroup).filter(
            and_(SecurityGroup.owner_id == user_id, SecurityGroup.name == name)
        ).first()
        
        if existing:
            raise ValueError(f"Security group '{name}' already exists")
        
        sg = SecurityGroup(
            name=name,
            description=description,
            owner_id=user_id,
            is_default=False
        )
        self.db.add(sg)
        self.db.commit()
        self.db.refresh(sg)
        
        return self._format_security_group(sg)
    
    def get_security_group(self, group_id: int, user_id: int) -> Optional[Dict]:
        """Get security group by ID"""
        sg = self.db.query(SecurityGroup).filter(
            and_(SecurityGroup.id == group_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not sg:
            return None
        
        return self._format_security_group(sg)
    
    def list_user_security_groups(self, user_id: int) -> List[Dict]:
        """List all security groups for a user"""
        sgs = self.db.query(SecurityGroup).filter(SecurityGroup.owner_id == user_id).all()
        return [self._format_security_group(sg) for sg in sgs]
    
    def delete_security_group(self, group_id: int, user_id: int) -> Dict:
        """Delete a security group"""
        sg = self.db.query(SecurityGroup).filter(
            and_(SecurityGroup.id == group_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not sg:
            raise ValueError("Security group not found")
        
        if sg.is_default:
            raise ValueError("Cannot delete default security group")
        
        self.db.query(VMSecurityGroup).filter(
            VMSecurityGroup.security_group_id == group_id
        ).delete()
        
        self.db.delete(sg)
        self.db.commit()
        
        return {"success": True, "message": f"Security group '{sg.name}' deleted"}
    
    # ============================================
    # Firewall Rule Operations
    # ============================================
    
    def add_rule(
        self,
        group_id: int,
        user_id: int,
        direction: str,
        protocol: str,
        port_range: Optional[str] = None,
        source_ip: str = "0.0.0.0/0",
        description: Optional[str] = None
    ) -> Dict:
        """Add a firewall rule to a security group"""
        
        sg = self.db.query(SecurityGroup).filter(
            and_(SecurityGroup.id == group_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not sg:
            raise ValueError("Security group not found")
        
        # Parse port range
        port_min, port_max = None, None
        if port_range and protocol in ['tcp', 'udp']:
            if '-' in port_range:
                parts = port_range.split('-')
                port_min = int(parts[0])
                port_max = int(parts[1])
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
            priority=(max_priority + 1) * 100,
            enabled=True
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        self._sync_security_group_acls(group_id)
        
        return self._format_rule(rule)
    
    def list_rules(self, group_id: int, user_id: int) -> List[Dict]:
        """List all rules in a security group"""
        sg = self.db.query(SecurityGroup).filter(
            and_(SecurityGroup.id == group_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not sg:
            raise ValueError("Security group not found")
        
        rules = self.db.query(FirewallRule).filter(
            FirewallRule.security_group_id == group_id
        ).order_by(FirewallRule.priority).all()
        
        return [self._format_rule(rule) for rule in rules]
    
    def update_rule(
        self,
        rule_id: int,
        user_id: int,
        direction: Optional[str] = None,
        protocol: Optional[str] = None,
        port_range: Optional[str] = None,
        source_ip: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict:
        """Update a firewall rule"""
        rule = self.db.query(FirewallRule).join(SecurityGroup).filter(
            and_(FirewallRule.id == rule_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not rule:
            raise ValueError("Rule not found")
        
        if direction:
            rule.direction = direction
        if protocol:
            rule.protocol = protocol
        if port_range and rule.protocol in ['tcp', 'udp']:
            if '-' in port_range:
                parts = port_range.split('-')
                rule.port_min = int(parts[0])
                rule.port_max = int(parts[1])
            else:
                rule.port_min = rule.port_max = int(port_range)
        if source_ip:
            rule.source_ip = source_ip
        if description is not None:
            rule.description = description
        
        self.db.commit()
        self.db.refresh(rule)
        
        self._sync_security_group_acls(rule.security_group_id)
        
        return self._format_rule(rule)
    
    def delete_rule(self, rule_id: int, user_id: int) -> Dict:
        """Delete a firewall rule"""
        rule = self.db.query(FirewallRule).join(SecurityGroup).filter(
            and_(FirewallRule.id == rule_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not rule:
            raise ValueError("Rule not found")
        
        group_id = rule.security_group_id
        self.db.delete(rule)
        self.db.commit()
        
        self._sync_security_group_acls(group_id)
        
        return {"success": True, "message": "Rule deleted"}
    
    def toggle_rule(self, rule_id: int, user_id: int, enabled: bool) -> Dict:
        """Enable or disable a firewall rule"""
        rule = self.db.query(FirewallRule).join(SecurityGroup).filter(
            and_(FirewallRule.id == rule_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not rule:
            raise ValueError("Rule not found")
        
        rule.enabled = enabled
        self.db.commit()
        
        self._sync_security_group_acls(rule.security_group_id)
        
        return self._format_rule(rule)
    
    # ============================================
    # VM Assignment Operations
    # ============================================
    
    def assign_to_vm(self, group_id: int, vm_id: int, user_id: int) -> Dict:
        """Assign security group to a VM"""
        
        sg = self.db.query(SecurityGroup).filter(
            and_(SecurityGroup.id == group_id, SecurityGroup.owner_id == user_id)
        ).first()
        
        if not sg:
            raise ValueError("Security group not found")
        
        vm = self.db.query(VM).filter(
            and_(VM.id == vm_id, VM.owner_id == user_id)
        ).first()
        
        if not vm:
            raise ValueError("VM not found")
        
        existing = self.db.query(VMSecurityGroup).filter(
            and_(
                VMSecurityGroup.vm_id == vm_id,
                VMSecurityGroup.security_group_id == group_id
            )
        ).first()
        
        if existing:
            raise ValueError("Security group already assigned to this VM")
        
        assignment = VMSecurityGroup(
            vm_id=vm_id,
            security_group_id=group_id
        )
        self.db.add(assignment)
        self.db.commit()
        
        self._apply_acls_to_vm(vm, sg)
        
        return {"success": True, "message": f"Security group assigned to VM"}
    
    def unassign_from_vm(self, group_id: int, vm_id: int, user_id: int) -> Dict:
        """Remove security group from a VM"""
        
        vm = self.db.query(VM).filter(
            and_(VM.id == vm_id, VM.owner_id == user_id)
        ).first()
        
        if not vm:
            raise ValueError("VM not found")
        
        result = self.db.query(VMSecurityGroup).filter(
            and_(
                VMSecurityGroup.vm_id == vm_id,
                VMSecurityGroup.security_group_id == group_id
            )
        ).delete()
        
        if result == 0:
            raise ValueError("Security group not assigned to this VM")
        
        self.db.commit()
        
        return {"success": True, "message": "Security group removed from VM"}
    
    def list_vm_security_groups(self, vm_id: int, user_id: int) -> List[Dict]:
        """List security groups assigned to a VM"""
        vm = self.db.query(VM).filter(
            and_(VM.id == vm_id, VM.owner_id == user_id)
        ).first()
        
        if not vm:
            raise ValueError("VM not found")
        
        assignments = self.db.query(VMSecurityGroup).filter(
            VMSecurityGroup.vm_id == vm_id
        ).all()
        
        sgs = []
        for assignment in assignments:
            sg = self.db.query(SecurityGroup).get(assignment.security_group_id)
            if sg:
                sgs.append(self._format_security_group(sg))
        
        return sgs
    
    # ============================================
    # Template Operations
    # ============================================
    
    def apply_template_web_server(self, group_id: int, user_id: int) -> Dict:
        """Apply web server template rules"""
        
        rules = [
            {"direction": "ingress", "protocol": "tcp", "port_range": "22", 
             "source_ip": "0.0.0.0/0", "description": "SSH"},
            {"direction": "ingress", "protocol": "tcp", "port_range": "80", 
             "source_ip": "0.0.0.0/0", "description": "HTTP"},
            {"direction": "ingress", "protocol": "tcp", "port_range": "443", 
             "source_ip": "0.0.0.0/0", "description": "HTTPS"},
            {"direction": "ingress", "protocol": "icmp", "port_range": None, 
             "source_ip": "0.0.0.0/0", "description": "Ping"},
            {"direction": "egress", "protocol": "all", "port_range": None, 
             "source_ip": "0.0.0.0/0", "description": "Allow all outbound"},
        ]
        
        added = []
        for rule_data in rules:
            rule = self.add_rule(group_id, user_id, **rule_data)
            added.append(rule)
        
        return {"template": "web-server", "rules_added": len(added)}
    
    def apply_template_database(self, group_id: int, user_id: int, vpc_cidr: str) -> Dict:
        """Apply database template rules"""
        
        rules = [
            {"direction": "ingress", "protocol": "tcp", "port_range": "22", 
             "source_ip": vpc_cidr, "description": "SSH from VPC"},
            {"direction": "ingress", "protocol": "tcp", "port_range": "3306", 
             "source_ip": vpc_cidr, "description": "MySQL from VPC"},
            {"direction": "ingress", "protocol": "tcp", "port_range": "5432", 
             "source_ip": vpc_cidr, "description": "PostgreSQL from VPC"},
            {"direction": "egress", "protocol": "all", "port_range": None, 
             "source_ip": "0.0.0.0/0", "description": "Allow all outbound"},
        ]
        
        added = []
        for rule_data in rules:
            rule = self.add_rule(group_id, user_id, **rule_data)
            added.append(rule)
        
        return {"template": "database", "rules_added": len(added)}
    
    # ============================================
    # OVN ACL Synchronization
    # ============================================
    
    def _sync_security_group_acls(self, group_id: int):
        """Sync all rules to OVN for all VMs in this security group"""
        assignments = self.db.query(VMSecurityGroup).filter(
            VMSecurityGroup.security_group_id == group_id
        ).all()
        
        sg = self.db.query(SecurityGroup).get(group_id)
        if not sg:
            return
        
        for assignment in assignments:
            vm = self.db.query(VM).get(assignment.vm_id)
            if vm and vm.vpc_id:
                self._apply_acls_to_vm(vm, sg)
    
    def _apply_acls_to_vm(self, vm: VM, sg: SecurityGroup):
        """Apply security group rules to a specific VM"""
        if not vm.vpc_id or not vm.private_ip:
            return
        
        vpc = self.db.query(Network).get(vm.vpc_id)
        if not vpc:
            return
        
        switch_name = f"vpc-{vpc.owner_id}-{vpc.name}".replace(' ', '-').lower()
        
        rules = self.db.query(FirewallRule).filter(
            and_(
                FirewallRule.security_group_id == sg.id,
                FirewallRule.enabled == True
            )
        ).order_by(FirewallRule.priority).all()
        
        for rule in rules:
            self._apply_acl_rule(switch_name, vm.private_ip, rule)
    
    def _apply_acl_rule(self, switch_name: str, vm_ip: str, rule: FirewallRule):
        """Apply a single ACL rule to OVN"""
        match_parts = []
        
        if rule.direction == "ingress":
            match_parts.append(f"ip4.dst == {vm_ip}")
        else:
            match_parts.append(f"ip4.src == {vm_ip}")
        
        if rule.protocol != "all":
            match_parts.append(rule.protocol)
        
        if rule.port_min:
            if rule.port_min == rule.port_max:
                match_parts.append(f"{rule.protocol}.dst == {rule.port_min}")
            else:
                match_parts.append(f"{rule.port_min} <= {rule.protocol}.dst <= {rule.port_max}")
        
        if rule.source_ip != "0.0.0.0/0":
            if rule.direction == "ingress":
                match_parts.append(f"ip4.src == {rule.source_ip}")
            else:
                match_parts.append(f"ip4.dst == {rule.source_ip}")
        
        match_str = " && ".join(match_parts)
        action = "allow-related" if rule.direction == "ingress" else "allow"
        ovn_direction = "to-lport" if rule.direction == "ingress" else "from-lport"
        
        try:
            self._run_ovn([
                "ovn-nbctl", "acl-add", switch_name,
                ovn_direction, str(rule.priority),
                match_str, action
            ])
        except:
            pass
    
    # ============================================
    # Helper Methods
    # ============================================
    
    def _format_security_group(self, sg: SecurityGroup) -> Dict:
        """Format security group for API response"""
        vm_count = self.db.query(VMSecurityGroup).filter(
            VMSecurityGroup.security_group_id == sg.id
        ).count()
        
        rule_count = self.db.query(FirewallRule).filter(
            FirewallRule.security_group_id == sg.id
        ).count()
        
        return {
            "id": sg.id,
            "name": sg.name,
            "description": sg.description,
            "is_default": sg.is_default,
            "vm_count": vm_count,
            "rule_count": rule_count,
            "created_at": sg.created_at
        }
    
    def _format_rule(self, rule: FirewallRule) -> Dict:
        """Format firewall rule for API response"""
        port_range = None
        if rule.port_min:
            if rule.port_min == rule.port_max:
                port_range = str(rule.port_min)
            else:
                port_range = f"{rule.port_min}-{rule.port_max}"
        
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
            "enabled": rule.enabled,
            "created_at": rule.created_at
        }