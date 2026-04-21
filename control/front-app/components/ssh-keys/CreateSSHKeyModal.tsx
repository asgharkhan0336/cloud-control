'use client';

import { useState } from 'react';
import { 
  X, 
  Key, 
  Info, 
  Loader2,
  Upload,
  FileText,
  Check,
  Copy,
  Eye,
  EyeOff,
  AlertTriangle,
  Terminal,
  Shield
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';

interface CreateSSHKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateSSHKeyModal({ isOpen, onClose, onSuccess }: CreateSSHKeyModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    public_key: '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [inputMethod, setInputMethod] = useState<'paste' | 'upload'>('paste');
  const [showKey, setShowKey] = useState(false);
  const [keyInfo, setKeyInfo] = useState<{
    type?: string;
    bits?: number;
    fingerprint?: string;
    comment?: string;
  }>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Key name is required';
    } else if (!/^[a-zA-Z0-9-_ ]+$/.test(formData.name)) {
      newErrors.name = 'Only letters, numbers, spaces, hyphens and underscores allowed';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters';
    } else if (formData.name.length > 50) {
      newErrors.name = 'Name must be less than 50 characters';
    }

    if (!formData.public_key.trim()) {
      newErrors.public_key = 'SSH public key is required';
    } else {
      const keyValidation = validateSSHKey(formData.public_key);
      if (!keyValidation.valid) {
        newErrors.public_key = keyValidation.error || 'Invalid SSH public key format';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateSSHKey = (key: string) => {
    const trimmedKey = key.trim();
    
    // Check for valid SSH key format
    const sshKeyPattern = /^(ssh-(?:rsa|ed25519|dss|ecdsa)|ecdsa-sha2-nistp(?:256|384|521))\s+[A-Za-z0-9+/]+[=]{0,3}(\s+.+)?$/;
    
    if (!sshKeyPattern.test(trimmedKey)) {
      return { valid: false, error: 'Invalid SSH public key format' };
    }

    const parts = trimmedKey.split(/\s+/);
    const keyType = parts[0];
    const keyData = parts[1];
    const comment = parts.slice(2).join(' ') || undefined;

    // Decode and analyze key
    try {
      const decoded = atob(keyData);
      const keyLength = decoded.length;
      
      let bits = 0;
      if (keyType === 'ssh-rsa') {
        bits = keyLength * 8 - 64;
      } else if (keyType === 'ssh-ed25519') {
        bits = 256;
      } else if (keyType.includes('ecdsa')) {
        if (keyType.includes('256')) bits = 256;
        else if (keyType.includes('384')) bits = 384;
        else if (keyType.includes('521')) bits = 521;
      }

      // Simple fingerprint simulation (real implementation would use crypto)
      const fingerprint = generateFingerprint(keyData);

      setKeyInfo({
        type: formatKeyType(keyType),
        bits,
        fingerprint,
        comment,
      });

      return { valid: true };
    } catch {
      return { valid: false, error: 'Invalid key encoding' };
    }
  };

  const formatKeyType = (type: string): string => {
    const types: Record<string, string> = {
      'ssh-rsa': 'RSA',
      'ssh-ed25519': 'Ed25519',
      'ssh-dss': 'DSA',
      'ecdsa-sha2-nistp256': 'ECDSA (256-bit)',
      'ecdsa-sha2-nistp384': 'ECDSA (384-bit)',
      'ecdsa-sha2-nistp521': 'ECDSA (521-bit)',
    };
    return types[type] || type;
  };

  const generateFingerprint = (keyData: string): string => {
    // Simple fingerprint generation for display
    let hash = 0;
    for (let i = 0; i < keyData.length; i++) {
      const char = keyData.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    const hex = Math.abs(hash).toString(16).padStart(32, '0').toUpperCase();
    return hex.match(/.{2}/g)?.join(':') || hex;
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setFormData({ ...formData, public_key: content.trim() });
      setErrors({ ...errors, public_key: '' });
      validateSSHKey(content);
    };
    reader.readAsText(file);
  };

  const handleKeyChange = (value: string) => {
    setFormData({ ...formData, public_key: value });
    setErrors({ ...errors, public_key: '' });
    
    if (value.trim()) {
      validateSSHKey(value);
    } else {
      setKeyInfo({});
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setLoading(true);
    try {
      await apiClient.post('/ssh-keys', {
        name: formData.name,
        public_key: formData.public_key.trim(),
      });

      toast.success('SSH key added successfully!');
      onSuccess();
      handleClose();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add SSH key');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({ name: '', public_key: '' });
    setErrors({});
    setKeyInfo({});
    setInputMethod('paste');
    setShowKey(false);
    onClose();
  };

  const copyGenerationCommand = (type: string = 'ed25519') => {
    const command = `ssh-keygen -t ${type} -C "your_email@example.com"`;
    navigator.clipboard.writeText(command);
    toast.success('Command copied to clipboard!');
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
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Key className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Add SSH Key
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Secure shell key for passwordless authentication
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
            {/* Generate SSH Key Help */}
            <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-start space-x-3">
                <Terminal className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-900 dark:text-green-300 mb-2">
                    Don't have an SSH key? Generate one:
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between bg-gray-900 rounded-lg p-3">
                      <code className="text-sm text-green-400 font-mono">
                        ssh-keygen -t ed25519 -C "your_email@example.com"
                      </code>
                      <button
                        onClick={() => copyGenerationCommand('ed25519')}
                        className="p-1.5 hover:bg-gray-700 rounded transition-colors"
                      >
                        <Copy className="w-4 h-4 text-gray-400" />
                      </button>
                    </div>
                    <p className="text-xs text-green-700 dark:text-green-400">
                      Or use RSA: <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">ssh-keygen -t rsa -b 4096</code>
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Name Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Key Name <span className="text-red-500">*</span>
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
                placeholder="e.g., My Laptop"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-500">{errors.name}</p>
              )}
            </div>

            {/* Input Method Toggle */}
            <div>
              <div className="flex items-center space-x-4 mb-3">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Input Method:
                </label>
                <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                  <button
                    type="button"
                    onClick={() => setInputMethod('paste')}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      inputMethod === 'paste'
                        ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <FileText className="w-4 h-4 inline mr-1" />
                    Paste
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMethod('upload')}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      inputMethod === 'upload'
                        ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <Upload className="w-4 h-4 inline mr-1" />
                    Upload
                  </button>
                </div>
              </div>

              {/* Public Key Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Public Key <span className="text-red-500">*</span>
                </label>
                
                {inputMethod === 'paste' ? (
                  <div className="relative">
                    <textarea
                      value={formData.public_key}
                      onChange={(e) => handleKeyChange(e.target.value)}
                      className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono text-sm resize-none ${
                        errors.public_key 
                          ? 'border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                      placeholder="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host"
                      rows={4}
                      spellCheck={false}
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3 top-3 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors"
                    >
                      {showKey ? <EyeOff className="w-4 h-4 text-gray-500" /> : <Eye className="w-4 h-4 text-gray-500" />}
                    </button>
                  </div>
                ) : (
                  <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center hover:border-blue-500 dark:hover:border-blue-500 transition-colors cursor-pointer">
                    <input
                      type="file"
                      onChange={handleFileUpload}
                      accept=".pub,.txt,text/plain"
                      className="hidden"
                      id="ssh-key-upload"
                    />
                    <label htmlFor="ssh-key-upload" className="cursor-pointer">
                      <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Click to upload or drag and drop
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        .pub files or text files containing SSH public key
                      </p>
                      {formData.public_key && (
                        <p className="text-sm text-green-600 mt-2">
                          ✓ File loaded: {formData.public_key.substring(0, 50)}...
                        </p>
                      )}
                    </label>
                  </div>
                )}
                
                {errors.public_key && (
                  <p className="mt-1 text-sm text-red-500">{errors.public_key}</p>
                )}
              </div>
            </div>

            {/* Key Information Preview */}
            {keyInfo.type && (
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center space-x-2">
                  <Shield className="w-4 h-4" />
                  <span>Key Information</span>
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500 dark:text-gray-400">Type</p>
                    <p className="font-medium text-gray-900 dark:text-white">{keyInfo.type}</p>
                  </div>
                  {keyInfo.bits && (
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Strength</p>
                      <p className="font-medium text-gray-900 dark:text-white">{keyInfo.bits} bits</p>
                    </div>
                  )}
                  {keyInfo.fingerprint && (
                    <div className="col-span-2">
                      <p className="text-gray-500 dark:text-gray-400">Fingerprint</p>
                      <p className="font-mono text-xs text-gray-900 dark:text-white mt-1">
                        {keyInfo.fingerprint}
                      </p>
                    </div>
                  )}
                  {keyInfo.comment && (
                    <div className="col-span-2">
                      <p className="text-gray-500 dark:text-gray-400">Comment</p>
                      <p className="text-gray-900 dark:text-white">{keyInfo.comment}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Security Notice */}
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-800 dark:text-yellow-300">
                  <p className="font-medium mb-1">Security Notice</p>
                  <ul className="space-y-1 text-yellow-700 dark:text-yellow-400 list-disc list-inside">
                    <li>Never share your private key with anyone</li>
                    <li>Use strong key types (Ed25519 or RSA 4096-bit)</li>
                    <li>Keys provide full access to your VMs</li>
                    <li>You can add multiple keys for different devices</li>
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
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Adding...</span>
                </>
              ) : (
                <span>Add SSH Key</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}