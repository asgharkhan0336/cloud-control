'use client';

import { useState } from 'react';
import { 
  X, 
  Shield, 
  Info, 
  Loader2,
  Globe,
  Database,
  Lock,
  Server,
  Plus,
  Trash2,
  ChevronDown,
  Check
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';

interface CreateSecurityGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface FirewallRule {
  direction: 'ingress' | 'egress';
  protocol: 'tcp' | 'udp' | 'icmp' | 'all';
  port_range: string;
  source_ip: string;
  description: string;
}

const PROTOCOL_OPTIONS = [
  { value: 'tcp', label: 'TCP' },
  { value: 'udp', label: 'UDP' },
  { value: 'icmp', label: 'ICMP' },
  { value: 'all', label: 'All' },
];

const TEMPLATES = [
  {
    id: 'web-server',
    name: 'Web Server',
    icon: Globe,
    description: 'SSH, HTTP, HTTPS, and ICMP',
    color: 'blue',
    rules: [
      { direction: 'ingress' as const, protocol: 'tcp' as const, port_range: '22', source_ip: '0.0.0.0/0', description: 'SSH' },
      { direction: 'ingress' as const, protocol: 'tcp' as const, port_range: '80', source_ip: '0.0.0.0/0', description: 'HTTP' },
      { direction: 'ingress' as const, protocol: 'tcp' as const, port_range: '443', source_ip: '0.0.0.0/0', description: 'HTTPS' },
      { direction: 'ingress' as const, protocol: 'icmp' as const, port_range: '', source_ip: '0.0.0.0/0', description: 'Ping' },
      { direction: 'egress' as const, protocol: 'all' as const, port_range: '', source_ip: '0.0.0.0/0', description: 'All outbound' },
    ],
  },
  {
    id: 'database',
    name: 'Database',
    icon: Database,
    description: 'MySQL, PostgreSQL from VPC only',
    color: 'purple',
    rules: [
      { direction: 'ingress' as const, protocol: 'tcp' as const, port_range: '3306', source_ip: '', description: 'MySQL' },
      { direction: 'ingress' as const, protocol: 'tcp' as const, port_range: '5432', source_ip: '', description: 'PostgreSQL' },
      { direction: 'egress' as const, protocol: 'all' as const, port_range: '', source_ip: '0.0.0.0/0', description: 'All outbound' },
    ],
  },
  {
    id: 'strict',
    name: 'Strict SSH',
    icon: Lock,
    description: 'SSH only from specific IPs',
    color: 'red',
    rules: [
      { direction: 'ingress' as const, protocol: 'tcp' as const, port_range: '22', source_ip: '', description: 'SSH' },
      { direction: 'egress' as const, protocol: 'all' as const, port_range: '', source_ip: '0.0.0.0/0', description: 'All outbound' },
    ],
  },
  {
    id: 'custom',
    name: 'Custom',
    icon: Server,
    description: 'Start from scratch',
    color: 'gray',
    rules: [],
  },
];

export function CreateSecurityGroupModal({ isOpen, onClose, onSuccess }: CreateSecurityGroupModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });
  const [rules, setRules] = useState<FirewallRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [selectedTemplate, setSelectedTemplate] = useState<string>('custom');
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [editingRule, setEditingRule] = useState<FirewallRule | null>(null);
  const [currentRule, setCurrentRule] = useState<FirewallRule>({
    direction: 'ingress',
    protocol: 'tcp',
    port_range: '',
    source_ip: '0.0.0.0/0',
    description: '',
  });

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Security group name is required';
    } else if (!/^[a-zA-Z0-9-_ ]+$/.test(formData.name)) {
      newErrors.name = 'Only letters, numbers, spaces, hyphens and underscores allowed';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters';
    } else if (formData.name.length > 50) {
      newErrors.name = 'Name must be less than 50 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const applyTemplate = (templateId: string) => {
    setSelectedTemplate(templateId);
    const template = TEMPLATES.find(t => t.id === templateId);
    
    if (template && template.id !== 'custom') {
      let templateRules = [...template.rules];
      
      // For database template, prompt for VPC CIDR
      if (template.id === 'database') {
        const vpcCidr = prompt('Enter VPC CIDR for internal access (e.g., 10.0.0.0/24):', '10.0.0.0/24');
        if (vpcCidr) {
          templateRules = templateRules.map(rule => ({
            ...rule,
            source_ip: rule.direction === 'ingress' ? vpcCidr : rule.source_ip,
          }));
        }
      }
      
      // For strict template, prompt for allowed IPs
      if (template.id === 'strict') {
        const allowedIp = prompt('Enter allowed IP address or CIDR:', '');
        if (allowedIp) {
          templateRules = templateRules.map(rule => ({
            ...rule,
            source_ip: rule.direction === 'ingress' ? allowedIp : rule.source_ip,
          }));
        }
      }
      
      setRules(templateRules);
    } else {
      setRules([]);
    }
  };

  const addRule = () => {
    if (!currentRule.direction || !currentRule.protocol) return;
    
    setRules([...rules, { ...currentRule }]);
    setCurrentRule({
      direction: 'ingress',
      protocol: 'tcp',
      port_range: '',
      source_ip: '0.0.0.0/0',
      description: '',
    });
    setShowRuleForm(false);
  };

  const updateRule = () => {
    if (!editingRule) return;
    
    const index = rules.indexOf(editingRule);
    if (index > -1) {
      const newRules = [...rules];
      newRules[index] = { ...currentRule };
      setRules(newRules);
    }
    setEditingRule(null);
    setCurrentRule({
      direction: 'ingress',
      protocol: 'tcp',
      port_range: '',
      source_ip: '0.0.0.0/0',
      description: '',
    });
    setShowRuleForm(false);
  };

  const editRule = (rule: FirewallRule) => {
    setEditingRule(rule);
    setCurrentRule({ ...rule });
    setShowRuleForm(true);
  };

  const removeRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setLoading(true);
    try {
      // Create security group
      const response = await apiClient.post('/firewall/groups', {
        name: formData.name,
        description: formData.description || undefined,
      });

      const groupId = response.data?.id || response.id;

      // Add rules
      for (const rule of rules) {
        await apiClient.post(`/firewall/groups/${groupId}/rules`, {
          direction: rule.direction,
          protocol: rule.protocol,
          port_range: rule.port_range || undefined,
          source_ip: rule.source_ip,
          description: rule.description || undefined,
        });
      }

      toast.success('Security group created successfully!');
      onSuccess();
      handleClose();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create security group');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({ name: '', description: '' });
    setRules([]);
    setErrors({});
    setSelectedTemplate('custom');
    setShowRuleForm(false);
    setEditingRule(null);
    setCurrentRule({
      direction: 'ingress',
      protocol: 'tcp',
      port_range: '',
      source_ip: '0.0.0.0/0',
      description: '',
    });
    onClose();
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
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Create Firewall
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Security group with custom rules
              </p>
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
        <div className="overflow-y-auto max-h-[calc(90vh-180px)]">
          <div className="p-6 space-y-6">
            {/* Name and Description */}
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Firewall Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => {
                    setFormData({ ...formData, name: e.target.value });
                    setErrors({ ...errors, name: '' });
                  }}
                  className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                    errors.name 
                      ? 'border-red-500 focus:ring-red-500' 
                      : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder="e.g., web-servers"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-500">{errors.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description <span className="text-gray-400">(Optional)</span>
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
                  placeholder="e.g., Firewall rules for web servers"
                  rows={2}
                />
              </div>
            </div>

            {/* Templates */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Start from Template
              </label>
              <div className="grid grid-cols-2 gap-3">
                {TEMPLATES.map((template) => {
                  const Icon = template.icon;
                  const colorClasses = {
                    blue: 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20',
                    purple: 'border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-900/20',
                    red: 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20',
                    gray: 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800',
                  };
                  
                  return (
                    <button
                      key={template.id}
                      type="button"
                      onClick={() => applyTemplate(template.id)}
                      className={`p-4 border-2 rounded-xl text-left transition-all ${
                        selectedTemplate === template.id
                          ? `${colorClasses[template.color as keyof typeof colorClasses]} border-current`
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <div className="flex items-start space-x-3">
                        <Icon className={`w-5 h-5 flex-shrink-0 ${
                          template.color === 'blue' ? 'text-blue-600' :
                          template.color === 'purple' ? 'text-purple-600' :
                          template.color === 'red' ? 'text-red-600' :
                          'text-gray-600'
                        }`} />
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {template.name}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {template.description}
                          </p>
                          {template.rules.length > 0 && (
                            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                              {template.rules.length} rules
                            </p>
                          )}
                        </div>
                        {selectedTemplate === template.id && (
                          <Check className="w-4 h-4 text-blue-600 ml-auto" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Rules List */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Firewall Rules ({rules.length})
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setEditingRule(null);
                    setCurrentRule({
                      direction: 'ingress',
                      protocol: 'tcp',
                      port_range: '',
                      source_ip: '0.0.0.0/0',
                      description: '',
                    });
                    setShowRuleForm(true);
                  }}
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center space-x-1"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Rule</span>
                </button>
              </div>

              {rules.length === 0 ? (
                <div className="text-center py-8 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg">
                  <Shield className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500 dark:text-gray-400">No rules defined</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                    Add rules or select a template above
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {rules.map((rule, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                    >
                      <div className="flex items-center space-x-3">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          rule.direction === 'ingress'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                        }`}>
                          {rule.direction.toUpperCase()}
                        </span>
                        <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                          {rule.protocol.toUpperCase()}
                        </span>
                        {rule.port_range && (
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            Port: {rule.port_range}
                          </span>
                        )}
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          Source: {rule.source_ip}
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <button
                          type="button"
                          onClick={() => editRule(rule)}
                          className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                        >
                          <Plus className="w-4 h-4 rotate-45" />
                        </button>
                        <button
                          type="button"
                          onClick={() => removeRule(index)}
                          className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/20 rounded text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Rule Form Modal */}
            {showRuleForm && (
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-700/30">
                <h4 className="font-medium text-gray-900 dark:text-white mb-4">
                  {editingRule ? 'Edit Rule' : 'Add Rule'}
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                      Direction
                    </label>
                    <select
                      value={currentRule.direction}
                      onChange={(e) => setCurrentRule({ 
                        ...currentRule, 
                        direction: e.target.value as 'ingress' | 'egress' 
                      })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700"
                    >
                      <option value="ingress">Ingress (Inbound)</option>
                      <option value="egress">Egress (Outbound)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                      Protocol
                    </label>
                    <select
                      value={currentRule.protocol}
                      onChange={(e) => setCurrentRule({ 
                        ...currentRule, 
                        protocol: e.target.value as 'tcp' | 'udp' | 'icmp' | 'all',
                        port_range: e.target.value === 'icmp' || e.target.value === 'all' ? '' : currentRule.port_range
                      })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700"
                    >
                      {PROTOCOL_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {(currentRule.protocol === 'tcp' || currentRule.protocol === 'udp') && (
                    <div>
                      <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                        Port Range
                      </label>
                      <input
                        type="text"
                        value={currentRule.port_range}
                        onChange={(e) => setCurrentRule({ ...currentRule, port_range: e.target.value })}
                        placeholder="e.g., 80 or 8000-9000"
                        className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700"
                      />
                    </div>
                  )}

                  <div className={currentRule.protocol === 'tcp' || currentRule.protocol === 'udp' ? '' : 'col-span-2'}>
                    <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                      Source IP/CIDR
                    </label>
                    <input
                      type="text"
                      value={currentRule.source_ip}
                      onChange={(e) => setCurrentRule({ ...currentRule, source_ip: e.target.value })}
                      placeholder="0.0.0.0/0"
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                      Description (Optional)
                    </label>
                    <input
                      type="text"
                      value={currentRule.description}
                      onChange={(e) => setCurrentRule({ ...currentRule, description: e.target.value })}
                      placeholder="e.g., Allow SSH"
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700"
                    />
                  </div>
                </div>

                <div className="flex justify-end space-x-2 mt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowRuleForm(false);
                      setEditingRule(null);
                    }}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={editingRule ? updateRule : addRule}
                    className="px-3 py-1.5 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded"
                  >
                    {editingRule ? 'Update' : 'Add'}
                  </button>
                </div>
              </div>
            )}

            {/* Info Box */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-start space-x-3">
                <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-800 dark:text-blue-300">
                  <p className="font-medium mb-1">About Firewall Rules</p>
                  <ul className="space-y-1 text-blue-700 dark:text-blue-400 list-disc list-inside">
                    <li>Rules are evaluated in order (higher priority first)</li>
                    <li>Default policy: Deny all inbound, Allow all outbound</li>
                    <li>Changes take effect immediately on assigned VMs</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating...</span>
                </>
              ) : (
                <span>Create Firewall</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}