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
  MemoryStick,
  Calendar,
  ArrowLeft,
  Pencil,
  Trash2,
  Activity
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';
import Link from 'next/link';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface VMDetail {
  id: number;
  name: string;
  state: 'running' | 'stopped' | 'paused';
  memory: number;
  vcpus: number;
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
    rules: Array<{
      id: number;
      direction: string;
      protocol: string;
      port_range: string | null;
      source_ip: string;
    }>;
  }>;
  disk_usage: Record<string, number>;
  disk_size: number;
  os_variant: string;
  created_at: string;
  metrics: {
    cpu: Array<{ time: string; value: number }>;
    memory: Array<{ time: string; value: number }>;
    network: Array<{ time: string; in: number; out: number }>;
  };
}

export default function VMDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const vmId = parseInt(params.id as string);

  const { data: vm, isLoading, refetch } = useQuery({
    queryKey: ['vm', vmId],
    queryFn: async () => {
      const response = await apiClient.get(`/vms/${vmId}`);
      return response as VMDetail;
    },
    refetchInterval: 5000,
  });

  const startVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/start`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      toast.success('VM started');
    },
  });

  const stopVM = useMutation({
    mutationFn: () => apiClient.post(`/vms/${vmId}/stop`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vm', vmId] });
      toast.success('VM stopped');
    },
  });

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
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
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
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
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
              }`}>
                {vm.state}
              </span>
            </div>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Created {new Date(vm.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          {vm.state === 'stopped' ? (
            <button
              onClick={() => startVM.mutate()}
              className="btn btn-primary flex items-center gap-2"
            >
              <Power className="w-4 h-4" />
              Start
            </button>
          ) : vm.state === 'running' ? (
            <button
              onClick={() => stopVM.mutate()}
              className="btn btn-secondary flex items-center gap-2"
            >
              <PowerOff className="w-4 h-4" />
              Stop
            </button>
          ) : null}
          
          <button
            onClick={() => router.push(`/compute/${vmId}/console`)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Terminal className="w-4 h-4" />
            Console
          </button>
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
                <MemoryStick className="w-5 h-5 text-green-500" />
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
                  <p className="text-xl font-semibold">{vm.cpu_percent.toFixed(1)}%</p>
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
                    <p className="text-gray-500">Not assigned</p>
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
                      <Link
                        href={`/compute/${vmId}/floating-ips/assign`}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        Assign Floating IP
                      </Link>
                    </div>
                  )}
                </div>
              </div>

              {/* VPC & Subnet */}
              {vm.vpc_name && (
                <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <Network className="w-4 h-4 text-purple-500" />
                    <span className="font-medium">VPC</span>
                  </div>
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
                </div>
              )}
            </div>
          </div>

          {/* Security Groups */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h2 className="text-lg font-semibold">Firewall</h2>
              <Link
                href={`/compute/${vmId}/security-groups`}
                className="text-sm text-blue-600 hover:underline"
              >
                Manage
              </Link>
            </div>
            <div className="card-body">
              {vm.security_groups.length === 0 ? (
                <div className="text-center py-6">
                  <Shield className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500">No security groups assigned</p>
                  <Link
                    href={`/compute/${vmId}/security-groups/assign`}
                    className="mt-2 inline-block text-sm text-blue-600 hover:underline"
                  >
                    Assign Security Group
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {vm.security_groups.map((sg) => (
                    <div key={sg.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <Link
                          href={`/firewall/groups/${sg.id}`}
                          className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {sg.name}
                        </Link>
                        <span className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                          {sg.rules.length} rules
                        </span>
                      </div>
                      {sg.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                          {sg.description}
                        </p>
                      )}
                      <div className="space-y-2">
                        {sg.rules.slice(0, 5).map((rule) => (
                          <div key={rule.id} className="flex items-center gap-2 text-sm">
                            <span className={`w-16 text-xs px-2 py-0.5 rounded ${
                              rule.direction === 'ingress'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}>
                              {rule.direction}
                            </span>
                            <span className="w-16 font-mono">{rule.protocol}</span>
                            <span className="font-mono text-gray-600">
                              {rule.port_range || 'All'}
                            </span>
                            <span className="text-gray-500">from</span>
                            <span className="font-mono">{rule.source_ip}</span>
                          </div>
                        ))}
                        {sg.rules.length > 5 && (
                          <Link
                            href={`/firewall/groups/${sg.id}`}
                            className="text-sm text-blue-600 hover:underline"
                          >
                            +{sg.rules.length - 5} more rules
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Metrics */}
        <div className="space-y-6">
          {/* CPU Chart */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">CPU Usage</h2>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={vm.metrics.cpu}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Network Chart */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">Network Traffic</h2>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={vm.metrics.network}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="in" stroke="#10b981" strokeWidth={2} dot={false} name="Inbound" />
                  <Line type="monotone" dataKey="out" stroke="#f59e0b" strokeWidth={2} dot={false} name="Outbound" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Actions */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">Actions</h2>
            </div>
            <div className="card-body space-y-2">
              <button className="w-full btn btn-secondary flex items-center justify-center gap-2">
                <Pencil className="w-4 h-4" />
                Resize
              </button>
              <button className="w-full btn btn-secondary flex items-center justify-center gap-2">
                <HardDrive className="w-4 h-4" />
                Snapshot
              </button>
              <button className="w-full btn btn-danger flex items-center justify-center gap-2">
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}