// app/(dashboard)/compute/create/page.tsx
// KEY CHANGES: Proper API integration following VPC patterns

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Check, Server, HardDrive, Key,
  Shield, Tag,
  DollarSign, Globe, Lock, Network, ChevronDown, ChevronRight,
  Loader2, Info
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { apiClient } from '@/lib/api/client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// ============================================
// Types - Following VPC API Response Patterns
// ============================================

interface VPCResponse {
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

interface SubnetResponse {
  id: number;
  name: string;
  cidr: string;
  gateway: string;
  available_ips: number;
  is_public: boolean;
}

interface SecurityGroupResponse {
  id: number;
  name: string;
  description?: string;
  is_default: boolean;
  vm_count: number;
  rule_count: number;
  created_at: string;
}

interface SSHKeyResponse {
  id: number;
  name: string;
  fingerprint: string;
  created_at: string;
}

// Request model - Following VPC's VPCCreate pattern
interface VMCreateRequest {
  name: string;
  memory: number;
  vcpus: number;
  disk_size: number;
  os_variant: string;
  vpc_id: number;
  subnet_id?: number;
  security_group_ids?: number[];
  ssh_key_ids?: number[];
  user_data?: string;
}

// Response model - Following VPCResponse pattern
interface VMResponse {
  name: string;
  state: string;
  memory: number;
  vcpus: number;
  cpu_percent: number;
  ip_addresses: string[];
  disk_usage: Record<string, number>;
  created_at?: string;
}

// ============================================
// API Hooks - Following the service pattern
// ============================================

const useVPCs = () => {
  return useQuery({
    queryKey: ['vpcs'],
    queryFn: async () => {
      const response = await apiClient.get<VPCResponse[]>('/vpc/');
      return response;
    },
  });
};

const useSubnets = (vpcId: number | null) => {
  return useQuery({
    queryKey: ['subnets', vpcId],
    queryFn: async () => {
      if (!vpcId) return [];
      const response = await apiClient.get<SubnetResponse[]>(`/vpc/${vpcId}/subnets`);
      return response;
    },
    enabled: !!vpcId,
  });
};

const useSecurityGroups = () => {
  return useQuery({
    queryKey: ['security-groups'],
    queryFn: async () => {
      const response = await apiClient.get<SecurityGroupResponse[]>('/firewall/groups');
      return response;
    },
  });
};

const useSSHKeys = () => {
  return useQuery({
    queryKey: ['ssh-keys'],
    queryFn: async () => {
      const response = await apiClient.get<SSHKeyResponse[]>('/ssh-keys');
      return response;
    },
  });
};

const useCreateVM = () => {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: async (data: VMCreateRequest) => {
      // Following VPC API pattern: POST to endpoint with JSON body
      const response = await apiClient.post<APIResponse<VMResponse>>('/vms', data);
      return response;
    },
    onSuccess: (data) => {
      // Invalidate VMs list cache
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('Server created successfully!');
      router.push('/compute');
    },
    onError: (error: any) => {
      // Following VPC API error pattern
      const detail = error.response?.data?.detail || 'Failed to create server';
      toast.error(detail);
    },
  });
};

// ============================================
// Constants
// ============================================

const SERVER_TYPES = {
  'shared-cost': { name: 'Shared - Cost Optimized', memory: 1024, vcpus: 1, price: 13.12 },
  'shared-regular': { name: 'Shared - Regular', memory: 2048, vcpus: 2, price: 27.74 },
  'dedicated-general': { name: 'Dedicated - General Purpose', memory: 4096, vcpus: 4, price: 62.02 },
} as const;

const OS_IMAGES = [
  { value: 'ubuntu24.04', label: 'Ubuntu 24.04 LTS', icon: '🐧' },
  { value: 'ubuntu22.04', label: 'Ubuntu 22.04 LTS', icon: '🐧' },
  { value: 'debian12', label: 'Debian 12', icon: '🐧' },
] as const;

type ServerTypeKey = keyof typeof SERVER_TYPES;
type SectionKey = 'type' | 'image' | 'networking' | 'ssh' | 'firewall' | 'name';

// ============================================
// Main Component
// ============================================

export default function CreateVMPage() {
  const router = useRouter();
  const [expandedVPCs, setExpandedVPCs] = useState<number[]>([]);
  
  // Form state
  const [config, setConfig] = useState({
    serverType: 'shared-regular' as ServerTypeKey,
    osImage: 'ubuntu24.04',
    selectedVPC: null as number | null,
    selectedSubnet: null as number | null,
    selectedSecurityGroups: [] as number[],
    selectedSSHKeys: [] as number[],
    name: '',
    userData: '',
  });

  // API Hooks
  const { data: vpcs, isLoading: vpcsLoading } = useVPCs();
  const { data: subnets, isLoading: subnetsLoading } = useSubnets(config.selectedVPC);
  const { data: securityGroups, isLoading: sgLoading } = useSecurityGroups();
  const { data: sshKeys, isLoading: sshLoading } = useSSHKeys();
  const createVM = useCreateVM();

  // Auto-expand selected VPC
  useEffect(() => {
    if (config.selectedVPC && !expandedVPCs.includes(config.selectedVPC)) {
      setExpandedVPCs(prev => [...prev, config.selectedVPC]);
    }
  }, [config.selectedVPC]);

  const toggleVPC = (vpcId: number) => {
    setExpandedVPCs(prev => 
      prev.includes(vpcId) ? prev.filter(id => id !== vpcId) : [...prev, vpcId]
    );
  };

  const selectVPC = (vpcId: number) => {
    setConfig({ 
      ...config, 
      selectedVPC: vpcId,
      selectedSubnet: null // Reset subnet when VPC changes
    });
  };

  const isSectionComplete = (sectionId: SectionKey): boolean => {
    switch(sectionId) {
      case 'type': return !!config.serverType;
      case 'image': return !!config.osImage;
      case 'networking': return !!config.selectedVPC;
      case 'ssh': return true;
      case 'firewall': return true;
      case 'name': return config.name.trim().length > 0;
      default: return false;
    }
  };

  const getPrice = () => {
    return SERVER_TYPES[config.serverType].price.toFixed(2);
  };

  const handleCreateServer = () => {
    // Validation - Following VPC API pattern
    if (!config.name || config.name.length < 3) {
      toast.error('Server name must be at least 3 characters');
      return;
    }
    
    if (!config.selectedVPC) {
      toast.error('Please select a VPC');
      return;
    }

    const serverType = SERVER_TYPES[config.serverType];
    
    // Build request - Following VPCCreate pattern
    const vmData: VMCreateRequest = {
      name: config.name,
      memory: serverType.memory,
      vcpus: serverType.vcpus,
      disk_size: 20,
      os_variant: config.osImage,
      vpc_id: config.selectedVPC,
      subnet_id: config.selectedSubnet || undefined,
      security_group_ids: config.selectedSecurityGroups.length > 0 ? config.selectedSecurityGroups : undefined,
      ssh_key_ids: config.selectedSSHKeys.length > 0 ? config.selectedSSHKeys : undefined,
      user_data: config.userData || undefined,
    };

    createVM.mutate(vmData);
  };

  // Section Card Component
  const SectionCard = ({ id, title, icon: Icon, children }: { 
    id: SectionKey; 
    title: string; 
    icon: any; 
    children: React.ReactNode;
  }) => {
    const isComplete = isSectionComplete(id);
    
    return (
      <div className={`bg-white border rounded-xl mb-4 overflow-hidden transition-all ${
        isComplete ? 'border-green-500' : 'border-gray-200'
      }`}>
        <div className={`px-6 py-5 border-b flex items-center gap-3 ${
          isComplete ? 'bg-green-50 border-green-200' : 'bg-white border-gray-100'
        }`}>
          <Icon size={20} className={isComplete ? 'text-green-600' : 'text-gray-500'} />
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          {isComplete && (
            <span className="ml-auto bg-green-600 text-white rounded-full px-3 py-1 text-xs font-medium flex items-center gap-1">
              <Check size={12} /> Complete
            </span>
          )}
        </div>
        <div className="p-6">
          {children}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex">
        {/* Main Content */}
        <div className="flex-1 p-8 max-w-4xl">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Create a Server</h1>
            <p className="text-gray-600 mt-1">Configure and deploy a new cloud server instance</p>
          </div>

          {/* Server Type Section */}
          <SectionCard id="type" title="Server Type" icon={Server}>
            <div className="grid grid-cols-1 gap-4">
              {(Object.entries(SERVER_TYPES) as [ServerTypeKey, typeof SERVER_TYPES[ServerTypeKey]][]).map(([key, type]) => (
                <button
                  key={key}
                  onClick={() => setConfig({ ...config, serverType: key })}
                  className={`border-2 rounded-xl p-5 text-left transition-all ${
                    config.serverType === key
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-gray-900">{type.name}</div>
                      <div className="text-sm text-gray-600 mt-1">
                        {type.vcpus} vCPU • {type.memory} MB RAM
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-gray-900">€{type.price.toFixed(2)}</div>
                      <div className="text-xs text-gray-500">/month</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </SectionCard>

          {/* OS Image Section */}
          <SectionCard id="image" title="Operating System" icon={HardDrive}>
            <div className="grid grid-cols-2 gap-3">
              {OS_IMAGES.map((os) => (
                <button
                  key={os.value}
                  onClick={() => setConfig({ ...config, osImage: os.value })}
                  className={`border-2 rounded-lg p-4 text-left transition-all ${
                    config.osImage === os.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{os.icon}</span>
                    <span className="font-medium text-gray-900">{os.label}</span>
                  </div>
                </button>
              ))}
            </div>
          </SectionCard>

          {/* Networking Section - VPC and Subnets */}
          <SectionCard id="networking" title="Networking" icon={Network}>
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800 flex gap-3">
                <Info size={18} className="flex-shrink-0" />
                <span>Select a VPC and subnet for your server. Each VPC provides isolated private networking.</span>
              </div>

              {/* VPC List */}
              {vpcsLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              ) : !vpcs?.length ? (
                <div className="text-center py-8 text-gray-500">
                  <Network className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p>No VPCs available</p>
                  <button 
                    onClick={() => router.push('/network/vpc/create')}
                    className="mt-3 text-blue-600 hover:text-blue-700 text-sm"
                  >
                    Create a VPC
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {vpcs.map((vpc) => (
                    <div key={vpc.id} className="border border-gray-200 rounded-lg overflow-hidden">
                      {/* VPC Header */}
                      <div
                        onClick={() => toggleVPC(vpc.id)}
                        className="p-4 cursor-pointer flex justify-between items-center hover:bg-gray-50"
                      >
                        <div className="flex items-center gap-3 flex-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              selectVPC(vpc.id);
                            }}
                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                              config.selectedVPC === vpc.id
                                ? 'border-blue-500 bg-blue-500'
                                : 'border-gray-300'
                            }`}
                          >
                            {config.selectedVPC === vpc.id && (
                              <div className="w-2 h-2 rounded-full bg-white" />
                            )}
                          </button>
                          <div>
                            <div className="font-medium text-gray-900 flex items-center gap-2">
                              {vpc.name}
                              {vpc.is_default && (
                                <span className="text-xs bg-gray-200 px-2 py-0.5 rounded text-gray-600">
                                  Default
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-gray-600">
                              CIDR: {vpc.cidr} • Gateway: {vpc.gateway} • {vpc.vm_count} VMs
                            </div>
                          </div>
                        </div>
                        {expandedVPCs.includes(vpc.id) ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      </div>

                      {/* Subnets List */}
                      {expandedVPCs.includes(vpc.id) && config.selectedVPC === vpc.id && (
                        <div className="border-t border-gray-200 bg-gray-50 p-4">
                          <div className="text-sm font-medium text-gray-700 mb-3">
                            Select Subnet
                          </div>
                          {subnetsLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                          ) : !subnets?.length ? (
                            <p className="text-sm text-gray-500">No subnets available</p>
                          ) : (
                            <div className="space-y-2">
                              {subnets.map((subnet) => (
                                <button
                                  key={subnet.id}
                                  onClick={() => setConfig({ ...config, selectedSubnet: subnet.id })}
                                  className={`w-full p-3 rounded-lg border text-left transition-all ${
                                    config.selectedSubnet === subnet.id
                                      ? 'border-blue-500 bg-blue-50'
                                      : 'border-gray-200 bg-white hover:border-gray-300'
                                  }`}
                                >
                                  <div className="flex justify-between items-center">
                                    <div>
                                      <div className="font-medium text-gray-900">{subnet.name}</div>
                                      <div className="text-sm text-gray-600">
                                        CIDR: {subnet.cidr} • Gateway: {subnet.gateway}
                                      </div>
                                    </div>
                                    <div className="text-right">
                                      <div className="text-sm font-medium text-green-600">
                                        {subnet.available_ips} IPs
                                      </div>
                                      <div className="text-xs text-gray-500">available</div>
                                    </div>
                                  </div>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </SectionCard>

          {/* Security Groups Section */}
          <SectionCard id="firewall" title="Firewall" icon={Shield}>
            <div className="space-y-3">
              {sgLoading ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                </div>
              ) : !securityGroups?.length ? (
                <p className="text-gray-500 text-center py-4">No security groups available</p>
              ) : (
                securityGroups.map((sg) => (
                  <label key={sg.id} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={config.selectedSecurityGroups.includes(sg.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setConfig({
                            ...config,
                            selectedSecurityGroups: [...config.selectedSecurityGroups, sg.id]
                          });
                        } else {
                          setConfig({
                            ...config,
                            selectedSecurityGroups: config.selectedSecurityGroups.filter(id => id !== sg.id)
                          });
                        }
                      }}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{sg.name}</div>
                      <div className="text-sm text-gray-600">
                        {sg.rule_count} rules • {sg.vm_count} VMs
                      </div>
                    </div>
                    {sg.is_default && (
                      <span className="text-xs bg-gray-200 px-2 py-1 rounded">Default</span>
                    )}
                  </label>
                ))
              )}
            </div>
          </SectionCard>

          {/* SSH Keys Section */}
          <SectionCard id="ssh" title="SSH Keys" icon={Key}>
            <div className="space-y-3">
              {sshLoading ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                </div>
              ) : !sshKeys?.length ? (
                <div className="text-center py-6 text-gray-500">
                  <Key className="w-10 h-10 mx-auto mb-2 text-gray-400" />
                  <p>No SSH keys found</p>
                  <button className="mt-2 text-blue-600 hover:text-blue-700 text-sm">
                    Add SSH Key
                  </button>
                </div>
              ) : (
                sshKeys.map((key) => (
                  <label key={key.id} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={config.selectedSSHKeys.includes(key.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setConfig({
                            ...config,
                            selectedSSHKeys: [...config.selectedSSHKeys, key.id]
                          });
                        } else {
                          setConfig({
                            ...config,
                            selectedSSHKeys: config.selectedSSHKeys.filter(id => id !== key.id)
                          });
                        }
                      }}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{key.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{key.fingerprint}</div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </SectionCard>

          {/* Server Name Section */}
          <SectionCard id="name" title="Server Name" icon={Tag}>
            <input
              type="text"
              value={config.name}
              onChange={(e) => setConfig({ ...config, name: e.target.value })}
              placeholder="e.g., prod-web-01"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => router.back()}
                className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateServer}
                disabled={!config.name || !config.selectedVPC || createVM.isPending}
                className="px-8 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {createVM.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Server'
                )}
              </button>
            </div>
          </SectionCard>
        </div>

        {/* Right Sidebar - Summary */}
        <div className="w-80 bg-white border-l border-gray-200 p-6 sticky top-0 h-screen overflow-y-auto">
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Estimated Cost
            </h3>
            <div className="flex items-baseline gap-1 mb-2">
              <span className="text-3xl font-bold text-gray-900">€{getPrice()}</span>
              <span className="text-sm text-gray-500">/mo</span>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Configuration Summary
            </h3>
            <div className="space-y-3">
              <SummaryRow label="Type" value={SERVER_TYPES[config.serverType].name} />
              <SummaryRow label="OS" value={OS_IMAGES.find(o => o.value === config.osImage)?.label || ''} />
              {config.selectedVPC && (
                <SummaryRow label="VPC" value={vpcs?.find(v => v.id === config.selectedVPC)?.name || ''} />
              )}
              {config.selectedSubnet && (
                <SummaryRow label="Subnet" value={subnets?.find(s => s.id === config.selectedSubnet)?.name || ''} />
              )}
              {config.name && <SummaryRow label="Name" value={config.name} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper component
function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-100">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm text-gray-900 font-medium">{value}</span>
    </div>
  );
}

// API Response type (following your backend pattern)
interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}