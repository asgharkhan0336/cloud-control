'use client';

import { useEffect, useState } from 'react';
import { 
  X, 
  Network, 
  Info, 
  Loader2,
  Check,
  Layers,
  Globe,
  Lock,
  AlertCircle
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';

interface CreateVPCModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface SubnetConfig {
  name: string;
  cidr: string;
  is_public: boolean;
}

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
  subnet_count: number;
}

interface SubnetOption {
  cidr: string;
  totalIps: number;
  usableIps: number;
  name: string;
  description: string;
}

interface ExistingSubnet {
  id: number;
  name: string;
  cidr: string;
  gateway: string;
  is_public: boolean;
}


export function CreateVPCModal({ isOpen, onClose, onSuccess }: CreateVPCModalProps) {
  const [step, setStep] = useState<'vpc' | 'subnet'>('vpc');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    cidr: '',
  });
  const [subnetConfig, setSubnetConfig] = useState<SubnetConfig>({
    name: 'default',
    cidr: '',
    is_public: false,
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [advancedMode, setAdvancedMode] = useState(false);
  const [createDefaultSubnet, setCreateDefaultSubnet] = useState(true);
  const [createdVPC, setCreatedVPC] = useState<VPCResponse | null>(null);

  const [ipRequirement, setIpRequirement] = useState<'small' | 'medium' | 'large' | 'custom'>('small');
  const [customIpCount, setCustomIpCount] = useState<number>(16);
  const [availableSubnets, setAvailableSubnets] = useState<SubnetOption[]>([]);
  const [selectedSubnetCidr, setSelectedSubnetCidr] = useState<string>('');
  const [existingSubnets, setExistingSubnets] = useState<ExistingSubnet[]>([]);
  const [loadingSubnets, setLoadingSubnets] = useState(false);

  const suggestedCIDRs = [
    { label: 'Small', value: '10.0.0.0/24', ips: 256, subnet: '10.0.0.0/26' },
    { label: 'Medium', value: '10.0.0.0/20', ips: 4096, subnet: '10.0.0.0/24' },
    { label: 'Large', value: '10.0.0.0/16', ips: 65536, subnet: '10.0.0.0/20' },
  ];

  const subnetOptions = [
    { label: 'Private Subnet', value: false, icon: Lock, description: 'Internal only, no direct internet access' },
    { label: 'Public Subnet', value: true, icon: Globe, description: 'Can assign floating IPs for internet access' },
  ];

  // IP requirement options
 const ipOptions = [
  { 
    value: 'small', 
    label: 'Small', 
    requiredIps: 11,  // Up to 11 VMs
    cidr: '/28',      // 16 total IPs, 11 usable
    description: 'Up to 11 VMs (/28 - 16 IPs)',
    icon: '🔹'
  },
  { 
    value: 'medium', 
    label: 'Medium', 
    requiredIps: 59,  // Up to 59 VMs
    cidr: '/26',      // 64 total IPs, 59 usable
    description: 'Up to 59 VMs (/26 - 64 IPs)',
    icon: '🔸'
  },
  { 
    value: 'large', 
    label: 'Large', 
    requiredIps: 251, // Up to 251 VMs
    cidr: '/24',      // 256 total IPs, 251 usable
    description: 'Up to 251 VMs (/24 - 256 IPs)',
    icon: '🔷'
  },
  { 
    value: 'custom', 
    label: 'Custom', 
    requiredIps: null, 
    cidr: null,
    description: 'Choose custom IP range',
    icon: '⚙️'
  },
];

   // Calculate possible subnets within VPC CIDR
const calculateAvailableSubnets = (vpcCidr: string, requiredIps: number, existing: ExistingSubnet[]) => {
  const [vpcIp, vpcPrefix] = vpcCidr.split('/');
  const vpcPrefixNum = parseInt(vpcPrefix);
  
  // Determine subnet prefix based on REQUIRED IPs (not state variable)
  // Add 5 reserved IPs: network, gateway, broadcast, +2 for future/AWS-style
  const totalIpsNeeded = requiredIps + 5;
  
  // Find the smallest power of 2 that fits the required IPs
  let subnetSize = 4; // Start at /30 (4 IPs)
  while (subnetSize < totalIpsNeeded) {
    subnetSize *= 2;
  }
  
  // Calculate prefix from subnet size
  // prefix = 32 - log2(subnetSize)
  let subnetPrefix = 32;
  let tempSize = subnetSize;
  while (tempSize > 1) {
    subnetPrefix--;
    tempSize /= 2;
  }
  
  // Ensure subnet prefix is larger than VPC prefix (subnet must be smaller than VPC)
  if (subnetPrefix <= vpcPrefixNum) {
    subnetPrefix = vpcPrefixNum + 1;
    subnetSize = Math.pow(2, 32 - subnetPrefix);
  }
  
  const subnets: SubnetOption[] = [];
  const vpcIpParts = vpcIp.split('.').map(Number);
  
  // Calculate number of possible subnets of this size
  const subnetBits = subnetPrefix - vpcPrefixNum;
  const numSubnets = Math.pow(2, subnetBits);
  
  // Calculate usable IPs (exclude network, gateway, broadcast, and 2 reserved)
  const usableIps = subnetSize - 5;
  
  // Generate subnet options
  const currentIpInt = (vpcIpParts[0] << 24) | (vpcIpParts[1] << 16) | (vpcIpParts[2] << 8) | vpcIpParts[3];
  
  for (let i = 0; i < Math.min(numSubnets, 16); i++) {
    const subnetIpInt = currentIpInt + (i * subnetSize);
    
    // Convert back to IP
    const subnetIp = `${(subnetIpInt >> 24) & 255}.${(subnetIpInt >> 16) & 255}.${(subnetIpInt >> 8) & 255}.${subnetIpInt & 255}`;
    const subnetCidr = `${subnetIp}/${subnetPrefix}`;
    
    // Check if this subnet overlaps with existing ones
    const overlaps = existing.some(existingSubnet => {
      return cidrOverlaps(subnetCidr, existingSubnet.cidr);
    });
    
    if (!overlaps) {
      const prefixMap: Record<number, string> = {
        16: '/16', 17: '/17', 18: '/18', 19: '/19', 20: '/20',
        21: '/21', 22: '/22', 23: '/23', 24: '/24', 25: '/25',
        26: '/26', 27: '/27', 28: '/28'
      };
      
      subnets.push({
        cidr: subnetCidr,
        totalIps: subnetSize,
        usableIps: usableIps,
        name: `Subnet ${i + 1} (${prefixMap[subnetPrefix] || `/${subnetPrefix}`})`,
        description: `${usableIps} usable IPs (${subnetSize} total)`,
      });
    }
  }
  
  return subnets;
};

  // Check if two CIDRs overlap
  const cidrOverlaps = (cidr1: string, cidr2: string): boolean => {
    try {
      const [ip1, prefix1] = cidr1.split('/');
      const [ip2, prefix2] = cidr2.split('/');
      
      const ip1Parts = ip1.split('.').map(Number);
      const ip2Parts = ip2.split('.').map(Number);
      
      const ip1Int = (ip1Parts[0] << 24) | (ip1Parts[1] << 16) | (ip1Parts[2] << 8) | ip1Parts[3];
      const ip2Int = (ip2Parts[0] << 24) | (ip2Parts[1] << 16) | (ip2Parts[2] << 8) | ip2Parts[3];
      
      const mask1 = ~((1 << (32 - parseInt(prefix1))) - 1);
      const mask2 = ~((1 << (32 - parseInt(prefix2))) - 1);
      
      const network1 = ip1Int & mask1;
      const network2 = ip2Int & mask2;
      
      const broadcast1 = network1 | (~mask1 >>> 0);
      const broadcast2 = network2 | (~mask2 >>> 0);
      
      return !(broadcast1 < network2 || broadcast2 < network1);
    } catch {
      return false;
    }
  };

  // Calculate network address for a CIDR
  const calculateNetworkAddress = (cidr: string): string => {
    try {
      const [ip, prefix] = cidr.split('/');
      const prefixNum = parseInt(prefix);
      
      const ipParts = ip.split('.').map(Number);
      const ipInt = (ipParts[0] << 24) | (ipParts[1] << 16) | (ipParts[2] << 8) | ipParts[3];
      
      const mask = ~((1 << (32 - prefixNum)) - 1);
      const networkInt = ipInt & mask;
      
      const networkParts = [
        (networkInt >> 24) & 255,
        (networkInt >> 16) & 255,
        (networkInt >> 8) & 255,
        networkInt & 255
      ];
      
      return `${networkParts.join('.')}/${prefixNum}`;
    } catch {
      return cidr;
    }
  };

// Fetch existing subnets
const fetchExistingSubnets = async (vpcId: number) => {
  setLoadingSubnets(true);
  try {
    const response = await apiClient.get(`/subnets?vpc_id=${vpcId}`);
    const subnets = response.data || response || [];
    setExistingSubnets(subnets);
    
    // Calculate initial available subnets
    let requiredIps = 16;
    if (ipRequirement === 'small') requiredIps = 16;
    else if (ipRequirement === 'medium') requiredIps = 64;
    else if (ipRequirement === 'large') requiredIps = 256;
    else requiredIps = customIpCount;
    
    const available = calculateAvailableSubnets(createdVPC!.cidr, requiredIps, subnets);
    setAvailableSubnets(available);
    
    if (available.length > 0) {
      setSelectedSubnetCidr(available[0].cidr);
    }
  } catch (error) {
    console.error('Failed to fetch subnets:', error);
    setExistingSubnets([]);
  } finally {
    setLoadingSubnets(false);
  }
};

// Calculate available subnets when IP requirement changes
const handleIpRequirementChange = (requirement: 'small' | 'medium' | 'large' | 'custom') => {
  setIpRequirement(requirement);
  
  if (createdVPC) {
    let requiredIps = 16;
    if (requirement === 'small') requiredIps = 11;   // For /28
    else if (requirement === 'medium') requiredIps = 59;  // For /26
    else if (requirement === 'large') requiredIps = 251;  // For /24
    else requiredIps = customIpCount;
    
    const subnets = calculateAvailableSubnets(createdVPC.cidr, requiredIps, existingSubnets);
    setAvailableSubnets(subnets);
    
    if (subnets.length > 0) {
      setSelectedSubnetCidr(subnets[0].cidr);
    } else {
      setSelectedSubnetCidr('');
    }
  }
};

// Calculate when custom IP count changes
const handleCustomIpChange = (count: number) => {
  setCustomIpCount(count);
  
  if (createdVPC && ipRequirement === 'custom') {
    const subnets = calculateAvailableSubnets(createdVPC.cidr, count, existingSubnets);
    setAvailableSubnets(subnets);
    
    if (subnets.length > 0 && !subnets.find(s => s.cidr === selectedSubnetCidr)) {
      setSelectedSubnetCidr(subnets[0].cidr);
    }
  }
};

  const validateVPCForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'VPC name is required';
    } else if (!/^[a-zA-Z0-9-]+$/.test(formData.name)) {
      newErrors.name = 'Only letters, numbers, and hyphens allowed';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters';
    } else if (formData.name.length > 50) {
      newErrors.name = 'Name must be less than 50 characters';
    }

    if (advancedMode && formData.cidr) {
      const cidrPattern = /^([0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/;
      if (!cidrPattern.test(formData.cidr)) {
        newErrors.cidr = 'Invalid CIDR format (e.g., 10.0.0.0/24)';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateSubnetForm = () => {
    const newErrors: Record<string, string> = {};

    if (createDefaultSubnet) {
      if (!subnetConfig.name.trim()) {
        newErrors.subnet_name = 'Subnet name is required';
      } else if (!/^[a-zA-Z0-9-]+$/.test(subnetConfig.name)) {
        newErrors.subnet_name = 'Only letters, numbers, and hyphens allowed';
      }

      if (subnetConfig.cidr) {
        const cidrPattern = /^([0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/;
        if (!cidrPattern.test(subnetConfig.cidr)) {
          newErrors.subnet_cidr = 'Invalid CIDR format';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

const handleVPCCreate = async () => {
  if (!validateVPCForm()) return;

  setLoading(true);
  try {
    const payload: any = {
      name: formData.name,
      description: formData.description || undefined,
    };

    if (advancedMode && formData.cidr) {
      payload.cidr = formData.cidr;
    }

    const response = await apiClient.post('/vpc', payload);
    const vpc: VPCResponse = response.data || response;
    
    setCreatedVPC(vpc);
    
    // Fetch existing subnets for this VPC (should be empty for new VPC)
    await fetchExistingSubnets(vpc.id);
    
    toast.success('VPC created successfully!');
    setStep('subnet');
  } catch (error: any) {
    toast.error(error.response?.data?.detail || 'Failed to create VPC');
  } finally {
    setLoading(false);
  }
};

const handleSubnetCreate = async () => {
    if (!validateSubnetForm()) return;
    if (!createdVPC) {
      toast.error('VPC information not found');
      return;
    }

    setLoading(true);
    try {
      if (createDefaultSubnet) {
        const subnetCidr = selectedSubnetCidr || (availableSubnets[0]?.cidr);
        
        if (!subnetCidr) {
          toast.error('No available subnet CIDR');
          return;
        }

        const validSubnetCidr = calculateNetworkAddress(subnetCidr);

        const subnetPayload = {
          name: subnetConfig.name,
          vpc_id: createdVPC.id,
          cidr: validSubnetCidr,
          is_public: subnetConfig.is_public,
        };

        await apiClient.post('/subnets', subnetPayload);
        toast.success('Default subnet created successfully!');
      }

      toast.success('VPC setup complete!');
      onSuccess();
      handleClose();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create subnet');
    } finally {
      setLoading(false);
    }
  };

  const handleSkipSubnet = () => {
    toast.success('VPC created! You can add subnets later.');
    onSuccess();
    handleClose();
  };

  const handleClose = () => {
    setFormData({ name: '', description: '', cidr: '' });
    setSubnetConfig({ name: 'default', cidr: '', is_public: false });
    setErrors({});
    setAdvancedMode(false);
    setCreateDefaultSubnet(true);
    setStep('vpc');
    setCreatedVPC(null);
    onClose();
  };

  const selectSuggestedCIDR = (cidr: string, subnetCidr: string) => {
    setFormData({ ...formData, cidr });
    setSubnetConfig({ ...subnetConfig, cidr: subnetCidr });
    setErrors({ ...errors, cidr: '' });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden">
        {/* Header with Steps */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Network className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {step === 'vpc' ? 'Create VPC' : 'Configure Subnet'}
              </h2>
              <div className="flex items-center space-x-2 mt-0.5">
                <span className={`text-sm ${step === 'vpc' ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>
                  1. VPC
                </span>
                <span className="text-gray-300">→</span>
                <span className={`text-sm ${step === 'subnet' ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>
                  2. Subnet
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto max-h-[calc(90vh-180px)]">
          {step === 'vpc' ? (
            <>
              {/* VPC Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  VPC Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => {
                    setFormData({ ...formData, name: e.target.value });
                    setErrors({ ...errors, name: '' });
                  }}
                  className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white transition-colors ${
                    errors.name 
                      ? 'border-red-500 focus:ring-red-500' 
                      : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder="e.g., production-vpc"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-500">{errors.name}</p>
                )}
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description <span className="text-gray-400">(Optional)</span>
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
                  placeholder="e.g., Production environment VPC"
                  rows={3}
                />
              </div>

              {/* Advanced Mode Toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setAdvancedMode(!advancedMode)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      advancedMode ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        advancedMode ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Advanced Mode (Custom CIDR)
                  </span>
                </div>
              </div>

              {/* CIDR Selection */}
              {advancedMode && (
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      CIDR Block
                    </label>
                    <input
                      type="text"
                      value={formData.cidr}
                      onChange={(e) => {
                        setFormData({ ...formData, cidr: e.target.value });
                        setErrors({ ...errors, cidr: '' });
                      }}
                      className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono ${
                        errors.cidr 
                          ? 'border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                      placeholder="e.g., 10.0.0.0/16"
                    />
                    {errors.cidr && (
                      <p className="mt-1 text-sm text-red-500">{errors.cidr}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Suggested CIDRs
                    </label>
                    <div className="space-y-2">
                      {suggestedCIDRs.map((cidr) => (
                        <button
                          key={cidr.value}
                          type="button"
                          onClick={() => selectSuggestedCIDR(cidr.value, cidr.subnet)}
                          className={`w-full p-3 border rounded-lg text-left transition-colors ${
                            formData.cidr === cidr.value
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white">
                                {cidr.label}
                              </p>
                              <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                                {cidr.value}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                {cidr.ips.toLocaleString()} IPs
                              </p>
                              {formData.cidr === cidr.value && (
                                <Check className="w-4 h-4 text-blue-600 inline ml-1" />
                              )}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div className="flex items-start space-x-3">
                  <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-800 dark:text-blue-300">
                    <p className="font-medium mb-1">Next Step: Subnet Configuration</p>
                    <p>After creating the VPC, you'll configure a default subnet for your resources.</p>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Success Message */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg mb-4">
                <div className="flex items-center space-x-2">
                  <Check className="w-5 h-5 text-green-600" />
                  <span className="text-sm font-medium text-green-900 dark:text-green-300">
                    VPC "{createdVPC?.name}" created successfully!
                  </span>
                </div>
                {createdVPC && (
                  <p className="text-xs text-green-700 dark:text-green-400 mt-1 ml-7">
                    CIDR: {createdVPC.cidr} • Gateway: {createdVPC.gateway}
                  </p>
                )}
              </div>

              {/* Create Subnet Toggle */}
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Create default subnet
                </label>
                <button
                  type="button"
                  onClick={() => setCreateDefaultSubnet(!createDefaultSubnet)}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                    createDefaultSubnet ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      createDefaultSubnet ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              {createDefaultSubnet ? (
                <div className="space-y-4">
        {/* Subnet Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Subnet Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={subnetConfig.name}
            onChange={(e) => {
              setSubnetConfig({ ...subnetConfig, name: e.target.value });
              setErrors({ ...errors, subnet_name: '' });
            }}
            className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
              errors.subnet_name 
                ? 'border-red-500 focus:ring-red-500' 
                : 'border-gray-300 dark:border-gray-600'
            }`}
            placeholder="e.g., default"
          />
          {errors.subnet_name && (
            <p className="mt-1 text-sm text-red-500">{errors.subnet_name}</p>
          )}
        </div>

        {/* IP Requirement Selection */}
       <div>
  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
    How many IPs do you need?
  </label>
  <div className="grid grid-cols-2 gap-3">
    {ipOptions.map((option) => (
      <button
        key={option.value}
        type="button"
        onClick={() => handleIpRequirementChange(option.value as any)}
        className={`p-4 border-2 rounded-lg text-left transition-all ${
          ipRequirement === option.value
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
        }`}
      >
        <div className="text-2xl mb-2">{option.icon}</div>
        <p className="font-medium text-gray-900 dark:text-white">
          {option.label}
        </p>
        {option.ips && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {option.description}
          </p>
        )}
      </button>
    ))}
  </div>
</div>

        {/* Custom IP Count */}
       {/* Custom IP Count */}
{ipRequirement === 'custom' && (
  <div>
    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
      Number of IPs needed
    </label>
    <input
      type="number"
      value={customIpCount}
      onChange={(e) => handleCustomIpChange(Math.max(8, Math.min(4096, parseInt(e.target.value) || 16)))}
      min={8}
      max={4096}
      className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
    />
  </div>
)}

        {/* Available Subnets */}
        {availableSubnets.length > 0 ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Available Subnets ({availableSubnets.length})
            </label>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {availableSubnets.map((subnet) => (
                <button
                  key={subnet.cidr}
                  type="button"
                  onClick={() => setSelectedSubnetCidr(subnet.cidr)}
                  className={`w-full p-3 border rounded-lg text-left transition-colors ${
                    selectedSubnetCidr === subnet.cidr
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-mono text-sm text-gray-900 dark:text-white">
                        {subnet.cidr}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {subnet.description}
                      </p>
                    </div>
                    {selectedSubnetCidr === subnet.cidr && (
                      <Check className="w-4 h-4 text-blue-600" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-800 dark:text-yellow-300">
                <p className="font-medium mb-1">No subnets available</p>
                <p>Try selecting a different IP requirement or VPC CIDR.</p>
              </div>
            </div>
          </div>
        )}

        {/* Subnet Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Subnet Type
          </label>
          <div className="grid grid-cols-2 gap-3">
            {subnetOptions.map((option) => {
              const Icon = option.icon;
              return (
                <button
                  key={option.label}
                  type="button"
                  onClick={() => setSubnetConfig({ ...subnetConfig, is_public: option.value })}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    subnetConfig.is_public === option.value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className={`w-5 h-5 mb-2 ${
                    subnetConfig.is_public === option.value ? 'text-blue-600' : 'text-gray-400'
                  }`} />
                  <p className="font-medium text-gray-900 dark:text-white">
                    {option.label}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {option.description}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </div>
              ) : (
                <div className="p-6 text-center">
                  <Layers className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600 dark:text-gray-400">
                    You can add subnets later from the VPC details page.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between">
            <div>
              {step === 'subnet' && (
                <button
                  type="button"
                  onClick={handleSkipSubnet}
                  className="text-gray-500 hover:text-gray-700 text-sm"
                >
                  Skip for now
                </button>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={step === 'vpc' ? handleClose : () => setStep('vpc')}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {step === 'vpc' ? 'Cancel' : 'Back'}
              </button>
              <button
                onClick={step === 'vpc' ? handleVPCCreate : handleSubnetCreate}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating...</span>
                  </>
                ) : (
                  <span>{step === 'vpc' ? 'Continue to Subnet' : 'Complete Setup'}</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper function to calculate proper network address
const calculateNetworkAddress = (cidr: string): string => {
  try {
    const [ip, prefix] = cidr.split('/');
    const prefixNum = parseInt(prefix);
    
    // Convert IP to integer
    const ipParts = ip.split('.').map(Number);
    const ipInt = (ipParts[0] << 24) | (ipParts[1] << 16) | (ipParts[2] << 8) | ipParts[3];
    
    // Calculate network mask
    const mask = ~((1 << (32 - prefixNum)) - 1);
    
    // Calculate network address
    const networkInt = ipInt & mask;
    
    // Convert back to dotted decimal
    const networkParts = [
      (networkInt >> 24) & 255,
      (networkInt >> 16) & 255,
      (networkInt >> 8) & 255,
      networkInt & 255
    ];
    
    return `${networkParts.join('.')}/${prefixNum}`;
  } catch {
    return cidr;
  }
};


const validateSubnetCIDR = (cidr: string): string | null => {
  if (!cidr) return null;
  
  const cidrPattern = /^([0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/;
  if (!cidrPattern.test(cidr)) {
    return 'Invalid CIDR format';
  }
  
  const [ip, prefix] = cidr.split('/');
  const prefixNum = parseInt(prefix);
  
  if (prefixNum < 16 || prefixNum > 28) {
    return 'Prefix must be between /16 and /28';
  }
  
  // Check if it's a valid network address
  const ipParts = ip.split('.').map(Number);
  const ipInt = (ipParts[0] << 24) | (ipParts[1] << 16) | (ipParts[2] << 8) | ipParts[3];
  const mask = ~((1 << (32 - prefixNum)) - 1);
  const networkInt = ipInt & mask;
  
  if (ipInt !== networkInt) {
    // Suggest the correct network address
    const networkParts = [
      (networkInt >> 24) & 255,
      (networkInt >> 16) & 255,
      (networkInt >> 8) & 255,
      networkInt & 255
    ];
    const correctCidr = `${networkParts.join('.')}/${prefixNum}`;
    return `Invalid network address. Did you mean ${correctCidr}?`;
  }
  
  return null;
};