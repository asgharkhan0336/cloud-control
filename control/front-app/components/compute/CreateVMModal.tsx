// components/compute/CreateVMModal.tsx
'use client';

import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';

interface CreateVMModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateVMModal({ isOpen, onClose, onSuccess }: CreateVMModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    memory: 2048,
    vcpus: 2,
    disk_size: 20,
    os_variant: 'ubuntu24.04',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await apiClient.post('/vms', formData);
      toast.success('VM created successfully');
      onSuccess();
    } catch (error) {
      toast.error('Failed to create VM');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Virtual Machine" size="lg">
      <form onSubmit={handleSubmit} className="p-6 space-y-4">
        <div>
          <label className="label">VM Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="input"
            placeholder="e.g., web-server-1"
            pattern="[a-zA-Z0-9-]+"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Memory (MB)</label>
            <select
              value={formData.memory}
              onChange={(e) => setFormData({ ...formData, memory: parseInt(e.target.value) })}
              className="input"
            >
              <option value={1024}>1 GB</option>
              <option value={2048}>2 GB</option>
              <option value={4096}>4 GB</option>
              <option value={8192}>8 GB</option>
              <option value={16384}>16 GB</option>
            </select>
          </div>

          <div>
            <label className="label">vCPUs</label>
            <select
              value={formData.vcpus}
              onChange={(e) => setFormData({ ...formData, vcpus: parseInt(e.target.value) })}
              className="input"
            >
              <option value={1}>1 vCPU</option>
              <option value={2}>2 vCPUs</option>
              <option value={4}>4 vCPUs</option>
              <option value={8}>8 vCPUs</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Disk Size (GB)</label>
          <input
            type="number"
            value={formData.disk_size}
            onChange={(e) => setFormData({ ...formData, disk_size: parseInt(e.target.value) })}
            className="input"
            min={5}
            max={1000}
            required
          />
        </div>

        <div>
          <label className="label">Operating System</label>
          <select
            value={formData.os_variant}
            onChange={(e) => setFormData({ ...formData, os_variant: e.target.value })}
            className="input"
          >
            <option value="ubuntu24.04">Ubuntu 24.04 LTS</option>
            <option value="ubuntu22.04">Ubuntu 22.04 LTS</option>
            <option value="debian12">Debian 12</option>
          </select>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
          >
            {loading ? 'Creating...' : 'Create VM'}
          </button>
        </div>
      </form>
    </Modal>
  );
}