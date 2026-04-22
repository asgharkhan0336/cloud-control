'use client';

import { useState, useRef, useEffect } from 'react';
import { 
  Server, 
  Plus, 
  Power, 
  PowerOff, 
  Trash2, 
  RefreshCw, 
  Clock, 
  Cpu, 
  HardDrive, 
  Activity,
  MoreVertical,
  Terminal,
  Copy,
  ExternalLink,
  Pause,
  RotateCw,
  Settings
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { VM } from '@/types';
import { toast } from 'react-hot-toast';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function ComputePage() {
  const queryClient = useQueryClient();
  const router = useRouter();

  const [expandedVM, setExpandedVM] = useState<string | null>(null);
  const [actionMenuVM, setActionMenuVM] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['vms'],
    queryFn: () => apiClient.get<{ vms: VM[]; total: number; running: number; stopped: number }>('/vms'),
  });

  const startVM = useMutation({
    mutationFn: (name: string) => apiClient.post(`/vms/${name}/start`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('VM started successfully');
    },
  });

  const stopVM = useMutation({
    mutationFn: (name: string) => apiClient.post(`/vms/${name}/stop`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('VM stopped successfully');
    },
  });

  const deleteVM = useMutation({
    mutationFn: (name: string) => apiClient.delete(`/vms/${name}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('VM deleted successfully');
      setActionMenuVM(null);
    },
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setActionMenuVM(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleCreateVM = () => router.push('/compute/create');

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
  };

  const vms = data?.vms || [];

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Compute Instances
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage your virtual machines
          </p>
        </div>
        <button onClick={handleCreateVM} className="btn btn-primary flex items-center space-x-2">
          <Plus className="w-4 h-4" />
          <span>Create VM</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-6">
          <p className="text-sm text-gray-500">Total VMs</p>
          <p className="text-3xl font-bold">{data?.total || 0}</p>
        </div>
        <div className="card p-6">
          <p className="text-sm text-gray-500">Running</p>
          <p className="text-3xl font-bold text-green-600">{data?.running || 0}</p>
        </div>
        <div className="card p-6">
          <p className="text-sm text-gray-500">Stopped</p>
          <p className="text-3xl font-bold text-gray-500">{data?.stopped || 0}</p>
        </div>
      </div>

      {/* List */}
      <div className="card">
        <div className="card-header flex justify-between items-center">
          <h2 className="text-lg font-semibold">Instances</h2>
          <button onClick={() => refetch()} className="p-2 hover:bg-gray-100 rounded-lg">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <div className="divide-y">
          {isLoading ? (
            <div className="py-12 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : vms.length === 0 ? (
            <div className="py-12 text-center">
              <Server className="w-10 h-10 mx-auto text-gray-400" />
              <p className="mt-2 text-gray-500">No instances yet</p>
            </div>
          ) : (
            vms.map((vm) => {
              const isExpanded = expandedVM === vm.name;

              return (
                <div key={vm.name} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <div className="flex justify-between items-start">
                    <div className="flex space-x-4">
                      <div className={`w-2 h-2 rounded-full mt-2 ${vm.state === 'running' ? 'bg-green-500' : 'bg-gray-400'}`} />
                      <div>
                        <button
                          onClick={() => setExpandedVM(isExpanded ? null : vm.name)}
                          className="font-medium text-left hover:text-blue-600 transition-colors"
                        >
                          {vm.name}
                        </button>

                        <p className="text-sm text-gray-500">
                          <Cpu className="inline w-3 h-3 mr-1" /> {vm.vcpus} vCPU
                          <span className="mx-2">•</span>
                          <HardDrive className="inline w-3 h-3 mr-1" /> {vm.memory} MB
                          <span className="mx-2">•</span>
                          Disk {Object.values(vm.disk_usage)[0] || 0} GB
                        </p>

                        {vm.ip_addresses?.length > 0 && (
                          <p className="text-sm text-gray-500 font-mono">
                            IP: {vm.ip_addresses.join(', ')}
                            <button
                              onClick={() => copyToClipboard(vm.ip_addresses[0], 'IP')}
                              className="ml-2 p-0.5 hover:bg-gray-200 rounded"
                            >
                              <Copy className="w-3 h-3 inline" />
                            </button>
                          </p>
                        )}

                        {/* Expanded details */}
                        {isExpanded && (
                          <div className="mt-3 space-y-1 text-sm text-gray-600 dark:text-gray-400">
                            {vm.created_at && <p>Created: {new Date(vm.created_at).toLocaleString()}</p>}
                            {'uptimeSeconds' in vm && (
                              <p><Clock className="inline w-3 h-3 mr-1" /> Uptime: {formatUptime((vm as any).uptimeSeconds)}</p>
                            )}
                            {'host' in vm && <p>Host: {(vm as any).host}</p>}
                            {'image' in vm && <p>Image: {(vm as any).image}</p>}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        vm.state === 'running' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                      }`}>
                        {vm.state}
                      </span>

                      {/* Quick Action Buttons */}
                      {vm.state === 'stopped' ? (
                        <button 
                          onClick={() => startVM.mutate(vm.name)} 
                          className="p-2 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                          title="Start VM"
                        >
                          <Power className="w-4 h-4" />
                        </button>
                      ) : vm.state === 'running' ? (
                        <button 
                          onClick={() => stopVM.mutate(vm.name)} 
                          className="p-2 text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded-lg transition-colors"
                          title="Stop VM"
                        >
                          <PowerOff className="w-4 h-4" />
                        </button>
                      ) : null}

                      {/* Dropdown Menu */}
                      <div className="relative" ref={actionMenuVM === vm.name ? menuRef : null}>
                        <button
                          onClick={() => setActionMenuVM(actionMenuVM === vm.name ? null : vm.name)}
                          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                          title="More actions"
                        >
                          <MoreVertical className="w-4 h-4 text-gray-500" />
                        </button>

                        {actionMenuVM === vm.name && (
                          <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                            <div className="py-1">
                              {/* View Details */}
                              <Link
                                href={`/compute/${vm.id}`}
                                className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                                onClick={() => setActionMenuVM(null)}
                              >
                                <ExternalLink className="w-4 h-4" />
                                View Details
                              </Link>

                              {/* Console */}
                              <button
                                onClick={() => {
                                  router.push(`/compute/${vm.name}/console`);
                                  setActionMenuVM(null);
                                }}
                                className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                              >
                                <Terminal className="w-4 h-4" />
                                Open Console
                              </button>

                              {/* Reboot (if running) */}
                              {vm.state === 'running' && (
                                <button
                                  onClick={() => {
                                    toast.success('Rebooting VM...');
                                    setActionMenuVM(null);
                                  }}
                                  className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                                >
                                  <RotateCw className="w-4 h-4" />
                                  Reboot
                                </button>
                              )}

                              {/* Pause (if running) */}
                              {vm.state === 'running' && (
                                <button
                                  onClick={() => {
                                    toast.success('Pausing VM...');
                                    setActionMenuVM(null);
                                  }}
                                  className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                                >
                                  <Pause className="w-4 h-4" />
                                  Pause
                                </button>
                              )}

                              {/* Copy IP */}
                              {vm.ip_addresses?.length > 0 && (
                                <button
                                  onClick={() => {
                                    copyToClipboard(vm.ip_addresses[0], 'IP address');
                                    setActionMenuVM(null);
                                  }}
                                  className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                                >
                                  <Copy className="w-4 h-4" />
                                  Copy IP Address
                                </button>
                              )}

                              {/* Settings */}
                              <button
                                onClick={() => {
                                  router.push(`/compute/${vm.name}/settings`);
                                  setActionMenuVM(null);
                                }}
                                className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                              >
                                <Settings className="w-4 h-4" />
                                Settings
                              </button>

                              <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>

                              {/* Delete */}
                              <button
                                onClick={() => {
                                  if (confirm(`Are you sure you want to delete "${vm.name}"?`)) {
                                    deleteVM.mutate(vm.name);
                                  }
                                  setActionMenuVM(null);
                                }}
                                className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                              >
                                <Trash2 className="w-4 h-4" />
                                Delete
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}