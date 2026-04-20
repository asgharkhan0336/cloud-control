// app/(dashboard)/compute/page.tsx
'use client';

import { useState } from 'react';
import { Server, Plus, Power, PowerOff, Trash2, RefreshCw } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { VM } from '@/types';
import { toast } from 'react-hot-toast';
import { CreateVMModal } from '@/components/compute/CreateVMModal';
import { useRouter } from 'next/navigation';

export default function ComputePage() {
  const queryClient = useQueryClient();
  const router = useRouter();

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
    },
  });

  const handleCreateVM = () => {
            router.push('/compute/create');

}

  const vms = data?.vms || [];

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
        <button
          onClick={() => handleCreateVM()}
          className="btn btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Create VM</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-6">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total VMs</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {data?.total || 0}
          </p>
        </div>
        <div className="card p-6">
          <p className="text-sm text-gray-500 dark:text-gray-400">Running</p>
          <p className="text-3xl font-bold text-green-600 mt-2">
            {data?.running || 0}
          </p>
        </div>
        <div className="card p-6">
          <p className="text-sm text-gray-500 dark:text-gray-400">Stopped</p>
          <p className="text-3xl font-bold text-gray-500 mt-2">
            {data?.stopped || 0}
          </p>
        </div>
      </div>

      {/* VM List */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Instances
          </h2>
          <button
            onClick={() => refetch()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : vms.length === 0 ? (
            <div className="text-center py-12">
              <Server className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No instances yet</p>
              <button
                onClick={() => handleCreateVM()}
                className="mt-4 btn btn-primary"
              >
                Create your first VM
              </button>
            </div>
          ) : (
            vms.map((vm) => (
              <div key={vm.name} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`w-2 h-2 rounded-full ${
                      vm.state === 'running' ? 'bg-green-500' : 'bg-gray-400'
                    }`} />
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        {vm.name}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {vm.vcpus} vCPU • {vm.memory} MB RAM • {Object.values(vm.disk_usage)[0] || 0} GB Disk
                      </p>
                      {vm.ip_addresses.length > 0 && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          IP: {vm.ip_addresses.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      vm.state === 'running'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                    }`}>
                      {vm.state}
                    </span>
                    
                    {vm.state === 'stopped' ? (
                      <button
                        onClick={() => startVM.mutate(vm.name)}
                        disabled={startVM.isPending}
                        className="p-2 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                      >
                        <Power className="w-4 h-4" />
                      </button>
                    ) : vm.state === 'running' ? (
                      <button
                        onClick={() => stopVM.mutate(vm.name)}
                        disabled={stopVM.isPending}
                        className="p-2 text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded-lg transition-colors"
                      >
                        <PowerOff className="w-4 h-4" />
                      </button>
                    ) : null}
                    
                    <button
                      onClick={() => {
                        if (confirm(`Delete VM "${vm.name}"?`)) {
                          deleteVM.mutate(vm.name);
                        }
                      }}
                      disabled={deleteVM.isPending}
                      className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* <CreateVMModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['vms'] });
          setShowCreateModal(false);
        }}
      /> */}
    </div>
  );
}