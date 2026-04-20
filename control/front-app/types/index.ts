// types/index.ts
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface VM {
  name: string;
  state: 'running' | 'stopped' | 'paused';
  memory: number;
  vcpus: number;
  cpu_percent: number;
  ip_addresses: string[];
  disk_usage: Record<string, number>;
  created_at?: string;
}

export interface VPC {
  id: number;
  name: string;
  description?: string;
  cidr: string;
  gateway: string;
  vni: number;
  is_default: boolean;
  created_at: string;
  vm_count: number;
}

export interface SecurityGroup {
  id: number;
  name: string;
  description?: string;
  is_default: boolean;
  vm_count: number;
  rule_count: number;
  created_at: string;
}

export interface FirewallRule {
  id: number;
  security_group_id: number;
  direction: 'ingress' | 'egress';
  protocol: 'tcp' | 'udp' | 'icmp' | 'all';
  port_min?: number;
  port_max?: number;
  port_range?: string;
  source_ip: string;
  description?: string;
  priority: number;
  enabled: boolean;
}

export interface PublicSubnet {
  id: number;
  name: string;
  cidr: string;
  gateway: string;
  router_ip: string;
  total_ips: number;
  allocated_ips: number;
  available_ips: number;
  created_at?: string;
}

export interface FloatingIP {
  id: number;
  ip_address: string;
  subnet_id: number;
  is_allocated: boolean;
  vm_name?: string;
}

export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}