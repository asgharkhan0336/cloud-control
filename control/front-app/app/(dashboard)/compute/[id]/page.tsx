'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  Server, 
  Power, 
  PowerOff, 
  RefreshCw,
  Globe,
  Lock,
  Shield,
  Network,
  Copy,
  Terminal,
  HardDrive,
  Cpu,
    Calendar,
  ArrowLeft,
  Pencil,
  Trash2,
  Activity,
  Pause,
  RotateCw,
  MoreVertical,
  AlertTriangle,
  MemoryStick
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';
import Link from 'next/link';

interface VMDetail {
  id: number;
  name: string;
  state: 'running' | 'stopped' | 'paused' | 'unknown';
  memory: number;
  vcpus: number;
  disk_size: number;
  cpu_percent: number;
  private_ip: string | null;
  floating_ip: string | null;
  vpc_id: number | null;
  vpc_name: string | null;
  vpc_cidr: string | null;
  subnet_id: number | null;
  subnet_name: string | null;
  subnet_cidr: string | null;
  security_groups: Array<{ 
    id: number; 
    name: string;
    description: string | null;
  }>;
  os_variant: string;
  created_at: string;
  owner_id: number;
}

export default function VMDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const vmId = parseInt(params.id as string);
  const [actionMenuOpen, setActionMenuOpen] = useState(false);

  const { data: vm, isLoading, refetch } = useQuery({
    queryKey: ['vm', vmId],
    queryFn: async () => {
      const response = await apiClient.get(`/vms/${vmId}`);
      return response as VMDetail;
    },
    refetchInterval: (query) => {
      const data = query.state.data as VMDetail | undefined;
      return data?.state === 'running' ? 5000 : false;
    },
  });

  const startVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/start`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('VM started');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start VM');
    },
  });

  const stopVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/stop`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('VM stopped');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to stop VM');
    },
  });

  const rebootVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/reboot`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      toast.success('VM rebooting');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to reboot VM');
    },
  });

  const pauseVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/pause`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      toast.success('VM paused');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to pause VM');
    },
  });

  const resumeVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/resume`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      toast.success('VM resumed');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to resume VM');
    },
  });

  const deleteVM = useMutation({
    mutationFn: () => apiClient.delete(`/vms/${vmId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      toast.success('VM deleted');
      router.push('/compute');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete VM');
    },
  });

  const copyToClipboard = (text: string, label: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete "${vm?.name}"? This action cannot be undone.`)) {
      deleteVM.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!vm) {
    return (
      <div className="text-center py-12">
        <Server className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <p className="text-gray-500">VM not found</p>
        <button
          onClick={() => router.push('/compute')}
          className="mt-4 text-blue-600 hover:underline"
        >
          Return to Compute
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/compute')}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {vm.name}
              </h1>
              <span className={`px-3 py-1 text-sm rounded-full ${
                vm.state === 'running'
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                  : vm.state === 'paused'
                  ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
              }`}>
                {vm.state}
              </span>
            </div>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Created {vm.created_at ? new Date(vm.created_at).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          {/* Power Actions */}
          {vm.state === 'stopped' && (
            <button
              onClick={() => startVM.mutate()}
              disabled={startVM.isPending}
              className="btn btn-primary flex items-center gap-2"
            >
              <Power className="w-4 h-4" />
              {startVM.isPending ? 'Starting...' : 'Start'}
            </button>
          )}
          
          {vm.state === 'running' && (
            <>
              <button
                onClick={() => stopVM.mutate()}
                disabled={stopVM.isPending}
                className="btn btn-secondary flex items-center gap-2"
              >
                <PowerOff className="w-4 h-4" />
                {stopVM.isPending ? 'Stopping...' : 'Stop'}
              </button>
              <button
                onClick={() => rebootVM.mutate()}
                disabled={rebootVM.isPending}
                className="btn btn-secondary flex items-center gap-2"
              >
                <RotateCw className="w-4 h-4" />
                Reboot
              </button>
            </>
          )}
          
          {vm.state === 'paused' && (
            <button
              onClick={() => resumeVM.mutate()}
              disabled={resumeVM.isPending}
              className="btn btn-primary flex items-center gap-2"
            >
              <Power className="w-4 h-4" />
              Resume
            </button>
          )}
          
          <button
            onClick={() => router.push(`/compute/${vmId}/console`)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Terminal className="w-4 h-4" />
            Console
          </button>

          {/* Actions Dropdown */}
          <div className="relative">
            <button
              onClick={() => setActionMenuOpen(!actionMenuOpen)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
            
            {actionMenuOpen && (
              <>
                <div 
                  className="fixed inset-0 z-10" 
                  onClick={() => setActionMenuOpen(false)}
                />
                <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20">
                  <div className="py-1">
                    {vm.state === 'running' && (
                      <button
                        onClick={() => {
                          pauseVM.mutate();
                          setActionMenuOpen(false);
                        }}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                      >
                        <Pause className="w-4 h-4" />
                        Pause
                      </button>
                    )}
                    <button
                      onClick={() => {
                        router.push(`/compute/${vmId}/resize`);
                        setActionMenuOpen(false);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                    >
                      <Pencil className="w-4 h-4" />
                      Resize
                    </button>
                    <button
                      onClick={() => {
                        router.push(`/compute/${vmId}/snapshots`);
                        setActionMenuOpen(false);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                    >
                      <HardDrive className="w-4 h-4" />
                      Snapshots
                    </button>
                    <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>
                    <button
                      onClick={() => {
                        handleDelete();
                        setActionMenuOpen(false);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Specifications */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">Specifications</h2>
            </div>
            <div className="card-body grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="flex items-center gap-3">
                <Cpu className="w-5 h-5 text-blue-500" />
                <div>
                  <p className="text-sm text-gray-500">vCPUs</p>
                  <p className="text-xl font-semibold">{vm.vcpus}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <MemoryStick  className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Memory</p>
                  <p className="text-xl font-semibold">{vm.memory} MB</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <HardDrive className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Disk</p>
                  <p className="text-xl font-semibold">{vm.disk_size} GB</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5 text-orange-500" />
                <div>
                  <p className="text-sm text-gray-500">CPU Usage</p>
                  <p className="text-xl font-semibold">{vm.cpu_percent?.toFixed(1) || '0.0'}%</p>
                </div>
              </div>
            </div>
            <div className="card-body border-t border-gray-200 dark:border-gray-700 pt-4">
              <div className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-gray-500" />
                <div>
                  <p className="text-sm text-gray-500">Operating System</p>
                  <p className="font-medium">{vm.os_variant || 'Ubuntu 24.04'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Networking */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">Networking</h2>
            </div>
            <div className="card-body space-y-4">
              {/* IP Addresses */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Lock className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium">Private IP</span>
                  </div>
                  {vm.private_ip ? (
                    <div className="flex items-center gap-2">
                      <code className="text-lg font-mono">{vm.private_ip}</code>
                      <button
                        onClick={() => copyToClipboard(vm.private_ip!, 'Private IP')}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-gray-500">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Not assigned</span>
                    </div>
                  )}
                </div>
                
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Globe className="w-4 h-4 text-blue-500" />
                    <span className="text-sm font-medium">Public IP</span>
                  </div>
                  {vm.floating_ip ? (
                    <div className="flex items-center gap-2">
                      <code className="text-lg font-mono">{vm.floating_ip}</code>
                      <button
                        onClick={() => copyToClipboard(vm.floating_ip!, 'Public IP')}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-500">Not assigned</p>
                      <button
                        onClick={() => router.push(`/compute/${vmId}/floating-ips/assign`)}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        Assign Floating IP
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* VPC & Subnet */}
              <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Network className="w-4 h-4 text-purple-500" />
                  <span className="font-medium">VPC</span>
                </div>
                {vm.vpc_name ? (
                  <div className="space-y-2">
                    <Link
                      href={`/network/vpc/${vm.vpc_id}`}
                      className="block text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {vm.vpc_name}
                    </Link>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      CIDR: {vm.vpc_cidr}
                    </p>
                    {vm.subnet_name && (
                      <>
                        <p className="text-sm font-medium mt-3">Subnet</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {vm.subnet_name} ({vm.subnet_cidr})
                        </p>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="text-gray-500">
                    <p>Not attached to any VPC</p>
                    <button
                      onClick={() => router.push(`/compute/${vmId}/network/attach`)}
                      className="mt-2 text-sm text-blue-600 hover:underline"
                    >
                      Attach to VPC
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Security Groups */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h2 className="text-lg font-semibold">Firewall</h2>
              <button
                onClick={() => router.push(`/compute/${vmId}/security-groups`)}
                className="text-sm text-blue-600 hover:underline"
              >
                Manage
              </button>
            </div>
            <div className="card-body">
              {!vm.security_groups || vm.security_groups.length === 0 ? (
                <div className="text-center py-6">
                  <Shield className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500">No security groups assigned</p>
                  <button
                    onClick={() => router.push(`/compute/${vmId}/security-groups/assign`)}
                    className="mt-2 inline-block text-sm text-blue-600 hover:underline"
                  >
                    Assign Security Group
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {vm.security_groups.map((sg) => (
                    <Link
                      key={sg.id}
                      href={`/firewall/groups/${sg.id}`}
                      className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {sg.name}
                          </p>
                          {sg.description && (
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {sg.description}
                            </p>
                          )}
                        </div>
                        <Shield className="w-5 h-5 text-green-500" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">Quick Actions</h2>
            </div>
            <div className="card-body space-y-2">
              <button
                onClick={() => router.push(`/compute/${vmId}/console`)}
                className="w-full btn btn-secondary flex items-center justify-center gap-2"
              >
                <Terminal className="w-4 h-4" />
                Open Console
              </button>
              {vm.private_ip && (
                <button
                  onClick={() => copyToClipboard(vm.private_ip!, 'Private IP')}
                  className="w-full btn btn-secondary flex items-center justify-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy Private IP
                </button>
              )}
              {vm.floating_ip && (
                <button
                  onClick={() => copyToClipboard(vm.floating_ip!, 'Public IP')}
                  className="w-full btn btn-secondary flex items-center justify-center gap-2"
                >
                  <Globe className="w-4 h-4" />
                  Copy Public IP
                </button>
              )}
            </div>
          </div>

          {/* Danger Zone */}
          <div className="card border-red-200 dark:border-red-800">
            <div className="card-header bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
              <h2 className="text-lg font-semibold text-red-800 dark:text-red-400">
                Danger Zone
              </h2>
            </div>
            <div className="card-body space-y-2">
              <button
                onClick={handleDelete}
                disabled={deleteVM.isPending}
                className="w-full btn btn-danger flex items-center justify-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                {deleteVM.isPending ? 'Deleting...' : 'Delete VM'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}