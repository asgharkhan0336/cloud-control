#!/bin/bash
# Cleanup script for cloud platform

set -e

echo "Cleaning up cloud platform..."

# Stop API service
systemctl stop cloud-platform-api 2>/dev/null || true

# Remove all VMs
for vm in $(virsh list --all --name); do
    if [[ -n "$vm" ]]; then
        echo "Removing VM: $vm"
        virsh destroy "$vm" 2>/dev/null || true
        virsh undefine "$vm" --remove-all-storage 2>/dev/null || true
    fi
done

# Remove custom networks
for net in $(virsh net-list --all --name | grep -v default); do
    if [[ -n "$net" ]]; then
        echo "Removing network: $net"
        virsh net-destroy "$net" 2>/dev/null || true
        virsh net-undefine "$net" 2>/dev/null || true
    fi
done

# Remove OVN bridges
ovs-vsctl del-br br-int 2>/dev/null || true
ovs-vsctl del-br br-ex 2>/dev/null || true

# Remove service file
rm -f /etc/systemd/system/cloud-platform-api.service
systemctl daemon-reload

echo "Cleanup completed"
