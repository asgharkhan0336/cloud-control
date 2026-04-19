#!/bin/bash
# Generate VM XML template for cloud-init

NAME=$1
MEMORY=${2:-2048}
VCPUS=${3:-2}
DISK_SIZE=${4:-20}

if [[ -z "$NAME" ]]; then
    echo "Usage: $0 <vm-name> [memory-mb] [vcpus] [disk-size-gb]"
    exit 1
fi

cat > "./templates/${NAME}-template.xml" << EOF
<domain type='kvm'>
  <name>${NAME}</name>
  <memory unit='MiB'>${MEMORY}</memory>
  <vcpu placement='static'>${VCPUS}</vcpu>
  <os>
    <type arch='x86_64' machine='pc-q35-6.2'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <virtio>
      <driver iommu='on'/>
    </virtio>
  </features>
  <cpu mode='host-passthrough' check='none' migratable='on'/>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='/var/lib/libvirt/images/${NAME}.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='bridge'>
      <source bridge='br-int'/>
      <virtualport type='openvswitch'/>
      <model type='virtio'/>
    </interface>
    <console type='pty'/>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
    </channel>
    <rng model='virtio'>
      <backend model='random'>/dev/urandom</backend>
    </rng>
  </devices>
</domain>
EOF

echo "Template created: ./templates/${NAME}-template.xml"
