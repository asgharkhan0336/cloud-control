## Base URL
http://localhost:8000/api/v1

text

## Authentication

### Register New User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "johnsmith",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "full_name": "John Smith"
}
Response:

json
{
  "id": 1,
  "username": "johnsmith",
  "email": "john@example.com",
  "full_name": "John Smith",
  "is_active": true,
  "is_superuser": false
}
Login
http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=johnsmith&password=SecurePass123!
Response:

json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "johnsmith",
    "email": "john@example.com",
    "full_name": "John Smith",
    "is_active": true,
    "is_superuser": false
  }
}
Get Current User
http
GET /auth/me
Authorization: Bearer {access_token}
Create API Key
http
POST /auth/api-keys
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "key_name": "my-app-key",
  "expires_days": 365
}
Response:

json
{
  "api_key": "cp_abc123...",
  "key_name": "my-app-key",
  "message": "Store this API key securely. It won't be shown again."
}
List API Keys
http
GET /auth/api-keys
Authorization: Bearer {access_token}
Revoke API Key
http
DELETE /auth/api-keys/{key_id}
Authorization: Bearer {access_token}
Virtual Machines (VMs)
List VMs
http
GET /vms
Authorization: Bearer {access_token}
Response:

json
{
  "vms": [
    {
      "name": "web-server-1",
      "state": "running",
      "memory": 2048,
      "vcpus": 2,
      "cpu_percent": 5.2,
      "ip_addresses": ["10.0.1.10", "159.69.1.10"],
      "disk_usage": {
        "/var/lib/libvirt/images/web-server-1.qcow2": 8
      }
    }
  ],
  "total": 1,
  "running": 1,
  "stopped": 0
}
Create VM
http
POST /vms
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "web-server-1",
  "memory": 2048,
  "vcpus": 2,
  "disk_size": 20,
  "os_variant": "ubuntu24.04",
  "network_bridge": "virbr0",
  "ssh_key": "ssh-rsa AAAAB3NzaC1yc2E..."
}
Response:

json
{
  "success": true,
  "message": "VM 'web-server-1' created successfully",
  "data": {
    "name": "web-server-1"
  }
}
Get VM Details
http
GET /vms/{name}
Authorization: Bearer {access_token}
Start VM
http
POST /vms/{name}/start
Authorization: Bearer {access_token}
Stop VM
http
POST /vms/{name}/stop
Authorization: Bearer {access_token}

# Force stop
POST /vms/{name}/stop?force=true
Delete VM
http
DELETE /vms/{name}
Authorization: Bearer {access_token}
VPC (Virtual Private Cloud)
List VPCs
http
GET /vpc
Authorization: Bearer {access_token}
Response:

json
[
  {
    "id": 1,
    "name": "production-vpc",
    "description": "Production environment",
    "cidr": "10.0.1.0/24",
    "gateway": "10.0.1.1",
    "vni": 10001,
    "is_default": true,
    "created_at": "2024-01-15T10:30:00Z",
    "vm_count": 3
  }
]
Create VPC
http
POST /vpc
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "staging-vpc",
  "description": "Staging environment",
  "subnet_cidr": "10.0.2.0/24"
}
Get VPC Details
http
GET /vpc/{vpc_id}
Authorization: Bearer {access_token}
Delete VPC
http
DELETE /vpc/{vpc_id}
Authorization: Bearer {access_token}
Create Subnet in VPC
http
POST /vpc/{vpc_id}/subnets
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "database-subnet",
  "cidr": "10.0.1.128/28"
}
List Subnets
http
GET /vpc/{vpc_id}/subnets
Authorization: Bearer {access_token}
VPC Peering
http
POST /vpc/{vpc_id}/peer
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "peer_vpc_id": 2,
  "peer_account_id": "user-456"
}
Accept VPC Peering
http
POST /vpc/peer/{peering_id}/accept
Authorization: Bearer {access_token}
Firewall / Security Groups
List Security Groups
http
GET /firewall/groups
Authorization: Bearer {access_token}
Create Security Group
http
POST /firewall/groups
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "web-servers",
  "description": "Security group for web servers"
}
Get Security Group Details
http
GET /firewall/groups/{group_id}
Authorization: Bearer {access_token}
Delete Security Group
http
DELETE /firewall/groups/{group_id}
Authorization: Bearer {access_token}
Add Firewall Rule
http
POST /firewall/groups/{group_id}/rules
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "direction": "ingress",
  "protocol": "tcp",
  "port_range": "80",
  "source_ip": "0.0.0.0/0",
  "description": "Allow HTTP"
}
Protocol Options: tcp, udp, icmp, all

Port Range Examples:

Single port: "80"

Port range: "8000-9000"

No port: null (for ICMP or 'all')

List Firewall Rules
http
GET /firewall/groups/{group_id}/rules
Authorization: Bearer {access_token}
Delete Firewall Rule
http
DELETE /firewall/rules/{rule_id}
Authorization: Bearer {access_token}
Enable/Disable Rule
http
PUT /firewall/rules/{rule_id}/toggle?enabled=true
Authorization: Bearer {access_token}
Assign Security Group to VM
http
POST /firewall/groups/{group_id}/assign/{vm_name}
Authorization: Bearer {access_token}
Remove Security Group from VM
http
DELETE /firewall/groups/{group_id}/unassign/{vm_name}
Authorization: Bearer {access_token}
Apply Web Server Template
http
POST /firewall/templates/web-server?group_id=1
Authorization: Bearer {access_token}
Adds rules for: SSH (22), HTTP (80), HTTPS (443)

Apply Database Template
http
POST /firewall/templates/database?group_id=1&vpc_cidr=10.0.1.0/24
Authorization: Bearer {access_token}
Adds rules for: MySQL (3306), PostgreSQL (5432) from VPC only

Public Subnets (Admin Only)
List Public Subnets
http
GET /subnets
Authorization: Bearer {admin_token}
Add Public Subnet
http
POST /subnets
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "public-subnet-1",
  "cidr": "159.69.1.0/28",
  "gateway": "159.69.1.1"
}
Remove Public Subnet
http
DELETE /subnets/{subnet_id}
Authorization: Bearer {admin_token}
Floating IPs
List Available Floating IPs
http
GET /subnets/floating-ips/available
Authorization: Bearer {access_token}

# Filter by subnet
GET /subnets/floating-ips/available?subnet_id=1
Assign Floating IP to VM
http
POST /subnets/floating-ips/assign?vm_name=web-server-1
Authorization: Bearer {access_token}

# Specify subnet
POST /subnets/floating-ips/assign?vm_name=web-server-1&subnet_id=1
Response:

json
{
  "assigned": true,
  "floating_ip": "159.69.1.10",
  "vm_name": "web-server-1",
  "private_ip": "10.0.1.10",
  "subnet_id": 1
}
Release Floating IP
http
POST /subnets/floating-ips/release?ip_address=159.69.1.10
Authorization: Bearer {access_token}
Host & Health
Health Check
http
GET /health
Response:

json
{
  "success": true,
  "message": "Service is healthy",
  "data": {
    "libvirt": "connected"
  }
}
Host Information
http
GET /host
Authorization: Bearer {access_token}
Response:

json
{
  "hostname": "compute-1",
  "model": "x86_64",
  "memory_total": 65536,
  "memory_free": 45000,
  "cpu_cores": 16,
  "cpu_threads": 32,
  "cpu_model": "Intel Xeon",
  "kvm_version": "QEMU 8.0.0",
  "libvirt_version": "9.0.0",
  "storage_pools": [...],
  "networks": [...]
}
Error Responses
400 Bad Request
json
{
  "detail": "VM 'web-server-1' already exists"
}
401 Unauthorized
json
{
  "detail": "Could not validate credentials"
}
403 Forbidden
json
{
  "detail": "VM quota exceeded. Maximum 10 VMs allowed."
}
404 Not Found
json
{
  "detail": "VM 'web-server-1' not found"
}
500 Internal Server Error
json
{
  "detail": "Failed to connect to libvirt"
}
Quick Examples
Complete VM Deployment
bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john&password=Pass123!" | jq -r '.access_token')

# 2. Create VPC
VPC_ID=$(curl -s -X POST http://localhost:8000/api/v1/vpc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-vpc"}' | jq -r '.id')

# 3. Create Security Group
SG_ID=$(curl -s -X POST http://localhost:8000/api/v1/firewall/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"web-sg"}' | jq -r '.id')

# 4. Add firewall rules
curl -X POST http://localhost:8000/api/v1/firewall/templates/web-server?group_id=$SG_ID \
  -H "Authorization: Bearer $TOKEN"

# 5. Create VM
curl -X POST http://localhost:8000/api/v1/vms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-web-server",
    "memory": 2048,
    "vcpus": 2,
    "disk_size": 20,
    "os_variant": "ubuntu24.04"
  }'

# 6. Assign security group
curl -X POST http://localhost:8000/api/v1/firewall/groups/$SG_ID/assign/my-web-server \
  -H "Authorization: Bearer $TOKEN"

# 7. Assign floating IP
curl -X POST "http://localhost:8000/api/v1/subnets/floating-ips/assign?vm_name=my-web-server" \
  -H "Authorization: Bearer $TOKEN"

# 8. Start VM
curl -X POST http://localhost:8000/api/v1/vms/my-web-server/start \
  -H "Authorization: Bearer $TOKEN"
Rate Limits
100 requests per minute per user

10 VM creations per hour per user

API Version
Current version: v1