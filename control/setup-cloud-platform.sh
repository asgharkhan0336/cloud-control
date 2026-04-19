#!/bin/bash
# Cloud Platform Setup Script - Ubuntu 24.04 (Noble Numbat) - FIXED
# Installs and configures KVM, libvirt, and Open vSwitch for cloud platform

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

log_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root or with sudo"
    exit 1
fi

# Install KVM and libvirt (FIXED package list)
log_step "Installing KVM and libvirt"

apt-get update
apt-get install -y \
    qemu-system-x86 \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    virtinst \
    virt-manager \
    virt-viewer \
    qemu-utils \
    cloud-image-utils \
    genisoimage \
    libguestfs-tools \
    libvirt-dev \
    python3-libvirt \
    libosinfo-bin \
    osinfo-db-tools \
    swtpm \
    swtpm-tools \
    cpu-checker

# Add user to groups
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG libvirt $SUDO_USER
    usermod -aG kvm $SUDO_USER
    log_info "Added user $SUDO_USER to libvirt and kvm groups"
fi

log_success "KVM and libvirt packages installed"

# Install Open vSwitch
log_step "Installing Open vSwitch"

apt-get install -y \
    openvswitch-switch \
    openvswitch-common \
    python3-openvswitch

log_success "Open vSwitch packages installed"

# Configure libvirt
log_step "Configuring libvirt"

systemctl enable libvirtd
systemctl restart libvirtd
sleep 2

if systemctl is-active --quiet libvirtd; then
    log_success "libvirtd service is running"
else
    log_error "Failed to start libvirtd service"
    exit 1
fi

# Setup default network
if ! virsh net-list --all | grep -q default; then
    virsh net-define /usr/share/libvirt/networks/default.xml
    virsh net-autostart default
    virsh net-start default
fi

# Setup default storage pool
if ! virsh pool-list --all | grep -q default; then
    mkdir -p /var/lib/libvirt/images
    virsh pool-define-as --name default --type dir --target /var/lib/libvirt/images
    virsh pool-autostart default
    virsh pool-start default
else
    if ! virsh pool-list | grep -q default; then
        virsh pool-start default
    fi
fi

log_success "libvirt configured"

# Configure Open vSwitch
log_step "Configuring Open vSwitch"

systemctl enable openvswitch-switch
systemctl restart openvswitch-switch
sleep 3

if systemctl is-active --quiet openvswitch-switch; then
    log_success "Open vSwitch service is running"
else
    log_error "Failed to start Open vSwitch"
    exit 1
fi

# Create OVS bridge
if ! ovs-vsctl br-exists ovs-br0; then
    ovs-vsctl add-br ovs-br0
    log_success "OVS bridge 'ovs-br0' created"
fi

# Create OVS network in libvirt
cat > /tmp/ovs-network.xml << 'EOF'
<network>
  <name>ovs-network</name>
  <forward mode='bridge'/>
  <bridge name='ovs-br0'/>
  <virtualport type='openvswitch'/>
  <portgroup name='default' default='yes'>
  </portgroup>
</network>
EOF

if ! virsh net-list --all | grep -q ovs-network; then
    virsh net-define /tmp/ovs-network.xml
    virsh net-autostart ovs-network
    virsh net-start ovs-network
    log_success "OVS network defined in libvirt"
fi

log_success "Open vSwitch configured"

# Download cloud images
log_step "Downloading Cloud Images"

IMAGES_DIR="/var/lib/libvirt/images/base"
mkdir -p "$IMAGES_DIR"

cd "$IMAGES_DIR"

# Ubuntu 24.04
if [[ ! -f "ubuntu-24.04-server-cloudimg-amd64.img" ]]; then
    log_info "Downloading Ubuntu 24.04 cloud image..."
    wget -q --show-progress https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img
fi

# Ubuntu 22.04
if [[ ! -f "ubuntu-22.04-server-cloudimg-amd64.img" ]]; then
    log_info "Downloading Ubuntu 22.04 cloud image..."
    wget -q --show-progress https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img
fi

# Debian 12
if [[ ! -f "debian-12-genericcloud-amd64.qcow2" ]]; then
    log_info "Downloading Debian 12 cloud image..."
    wget -q --show-progress https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2
fi

cd - > /dev/null

# Create symlinks
mkdir -p ./images
ln -sf "$IMAGES_DIR/ubuntu-24.04-server-cloudimg-amd64.img" ./images/ubuntu24.04.qcow2
ln -sf "$IMAGES_DIR/ubuntu-22.04-server-cloudimg-amd64.img" ./images/ubuntu22.04.qcow2
ln -sf "$IMAGES_DIR/debian-12-genericcloud-amd64.qcow2" ./images/debian12.qcow2

log_success "Cloud images ready"

# Setup Python environment
log_step "Setting up Python Environment"

apt-get install -y python3 python3-pip python3-venv python3-dev

if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    log_success "Python virtual environment created"
fi

if [[ -f "requirements.txt" ]]; then
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    deactivate
    log_success "Python dependencies installed"
fi

# Create systemd service
log_step "Creating Systemd Service"

cat > /etc/systemd/system/cloud-platform-api.service << EOF
[Unit]
Description=Cloud Platform API Service
After=network.target libvirtd.service openvswitch-switch.service
Wants=libvirtd.service openvswitch-switch.service

[Service]
Type=simple
User=${SUDO_USER:-root}
Group=${SUDO_USER:-root}
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="LIBVIRT_DEFAULT_URI=qemu:///system"
ExecStart=$(pwd)/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
log_success "Systemd service created"

# Cleanup
rm -f /tmp/ovs-network.xml

# Verification
log_step "Verifying Installation"

echo ""
echo "✓ KVM: $(kvm-ok 2>/dev/null | head -1 || echo 'Available')"
echo "✓ libvirt: $(virsh version --short 2>/dev/null | head -n1)"
echo "✓ Open vSwitch: $(ovs-vsctl --version 2>/dev/null | head -n1)"

echo ""
log_info "Available networks:"
virsh net-list --all

echo ""
log_info "OVS bridges:"
ovs-vsctl list-br

# Final summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║         ${GREEN}✓ Cloud Platform Setup Complete!${NC}                   ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next Steps:"
echo ""
echo "1. Start the API service:"
echo "   sudo systemctl start cloud-platform-api"
echo "   sudo systemctl enable cloud-platform-api"
echo ""
echo "2. Check status:"
echo "   sudo systemctl status cloud-platform-api"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/api/v1/health"
echo ""
echo "4. API Documentation:"
echo "   http://localhost:8000/api/docs"
echo ""
echo "Important: If you added your user to groups, log out and back in."
echo ""
