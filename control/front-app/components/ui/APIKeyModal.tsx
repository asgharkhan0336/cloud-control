// components/ui/APIKeyModal.tsx
'use client';

import { useState, useEffect } from 'react';
import { X, Copy, Key, Trash2, Plus, Check } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';

interface APIKey {
  id: number;
  key_name: string;
  is_active: boolean;
  last_used?: string;
  created_at: string;
  expires_at?: string;
}

interface APIKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function APIKeyModal({ isOpen, onClose }: APIKeyModalProps) {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyExpiry, setNewKeyExpiry] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchAPIKeys();
    }
  }, [isOpen]);

  const fetchAPIKeys = async () => {
    setLoading(true);
    try {
      const keys = await apiClient.get<APIKey[]>('/auth/api-keys');
      setApiKeys(keys);
    } catch (error) {
      toast.error('Failed to fetch API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a key name');
      return;
    }

    setLoading(true);
    try {
      const data: any = { key_name: newKeyName };
      if (newKeyExpiry) {
        data.expires_days = parseInt(newKeyExpiry);
      }

      const response = await apiClient.post<{ api_key: string; key_name: string }>(
        '/auth/api-keys',
        data
      );
      
      setGeneratedKey(response.api_key);
      setNewKeyName('');
      setNewKeyExpiry('');
      setShowCreate(false);
      fetchAPIKeys();
      toast.success('API key created successfully');
    } catch (error) {
      toast.error('Failed to create API key');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeKey = async (keyId: number) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;

    try {
      await apiClient.delete(`/auth/api-keys/${keyId}`);
      toast.success('API key revoked');
      fetchAPIKeys();
    } catch (error) {
      toast.error('Failed to revoke API key');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Copied to clipboard');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2">
            <Key className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              API Keys
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Generated Key Display */}
        {generatedKey && (
          <div className="mx-6 mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-400 mb-2">
              ⚠️ Save this API key now. It won't be shown again!
            </p>
            <div className="flex items-center space-x-2">
              <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-900 rounded-lg text-sm font-mono break-all">
                {generatedKey}
              </code>
              <button
                onClick={() => copyToClipboard(generatedKey)}
                className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={() => setGeneratedKey(null)}
              className="mt-2 text-sm text-blue-600 hover:text-blue-700"
            >
              I've saved this key
            </button>
          </div>
        )}

        {/* Create Key Form */}
        {showCreate ? (
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">
              Create New API Key
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-700 dark:text-gray-300 mb-2">
                  Key Name
                </label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g., Production Key"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 dark:text-gray-300 mb-2">
                  Expires In (days, optional)
                </label>
                <select
                  value={newKeyExpiry}
                  onChange={(e) => setNewKeyExpiry(e.target.value)}
                  className="input"
                >
                  <option value="">Never</option>
                  <option value="30">30 days</option>
                  <option value="90">90 days</option>
                  <option value="180">180 days</option>
                  <option value="365">365 days</option>
                </select>
              </div>
              <div className="flex space-x-3">
                <button onClick={handleCreateKey} className="btn btn-primary">
                  Create Key
                </button>
                <button
                  onClick={() => setShowCreate(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center space-x-2 text-blue-600 hover:text-blue-700"
            >
              <Plus className="w-4 h-4" />
              <span>Create New API Key</span>
            </button>
          </div>
        )}

        {/* API Keys List */}
        <div className="overflow-y-auto max-h-96">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-12">
              <Key className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">
                No API keys yet
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                Create your first API key to access the platform programmatically
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {apiKeys.map((key) => (
                <div key={key.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {key.key_name}
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        Created: {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used && ` • Last used: ${new Date(key.last_used).toLocaleDateString()}`}
                        {key.expires_at && ` • Expires: ${new Date(key.expires_at).toLocaleDateString()}`}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        key.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                      }`}>
                        {key.is_active ? 'Active' : 'Revoked'}
                      </span>
                      {key.is_active && (
                        <button
                          onClick={() => handleRevokeKey(key.id)}
                          className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            API keys provide full access to your account. Keep them secure and never share them.
          </p>
        </div>
      </div>
    </div>
  );
}