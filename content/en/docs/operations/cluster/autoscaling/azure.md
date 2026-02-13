---
title: "Cluster Autoscaler for Azure"
linkTitle: "Azure"
description: "Configure automatic node scaling in Azure with Talos Linux and VMSS."
weight: 20
---

This guide explains how to configure cluster-autoscaler for automatic node scaling in Azure with Talos Linux.

## Prerequisites

- Azure subscription with Contributor Service Principal
- `az` CLI installed
- Existing Talos Kubernetes cluster with Kilo WireGuard mesh
- Talos worker machine config

## Step 1: Create Azure Infrastructure

### 1.1 Login with Service Principal

```bash
az login --service-principal \
  --username "<APP_ID>" \
  --password "<PASSWORD>" \
  --tenant "<TENANT_ID>"
```

### 1.2 Create Resource Group

```bash
az group create \
  --name <resource-group> \
  --location <location>
```

### 1.3 Create VNet and Subnet

```bash
az network vnet create \
  --resource-group <resource-group> \
  --name cozystack-vnet \
  --address-prefix 10.2.0.0/16 \
  --subnet-name workers \
  --subnet-prefix 10.2.0.0/24 \
  --location <location>
```

### 1.4 Create Network Security Group

```bash
az network nsg create \
  --resource-group <resource-group> \
  --name cozystack-nsg \
  --location <location>

# Allow WireGuard
az network nsg rule create \
  --resource-group <resource-group> \
  --nsg-name cozystack-nsg \
  --name AllowWireGuard \
  --priority 100 \
  --direction Inbound \
  --access Allow \
  --protocol Udp \
  --destination-port-ranges 51820

# Allow Talos API
az network nsg rule create \
  --resource-group <resource-group> \
  --nsg-name cozystack-nsg \
  --name AllowTalosAPI \
  --priority 110 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --destination-port-ranges 50000

# Associate NSG with subnet
az network vnet subnet update \
  --resource-group <resource-group> \
  --vnet-name cozystack-vnet \
  --name workers \
  --network-security-group cozystack-nsg
```

### 1.5 Create Route Table for Kilo Routing

Azure SDN routes packets based on destination IP, not the Linux next-hop set by Kilo. Without a custom route table, reply traffic from non-leader nodes to remote subnets (e.g. on-premises networks) is sent to the Internet route and dropped, making non-leader nodes unreachable from outside Azure.

Create a route table that directs remote subnet traffic through the Kilo location leader:

```bash
# Create route table
az network route-table create \
  --resource-group <resource-group> \
  --name kilo-routes \
  --location <location>

# Add routes for each remote subnet reachable via Kilo WireGuard mesh
# Replace <leader-internal-ip> with the internal IP of the Kilo leader node in this subnet
az network route-table route create \
  --resource-group <resource-group> \
  --route-table-name kilo-routes \
  --name to-onprem \
  --address-prefix <on-premises-subnet-cidr> \
  --next-hop-type VirtualAppliance \
  --next-hop-ip-address <leader-internal-ip>

# Add route for WireGuard overlay IPs
az network route-table route create \
  --resource-group <resource-group> \
  --route-table-name kilo-routes \
  --name to-wireguard-ips \
  --address-prefix 100.66.0.0/16 \
  --next-hop-type VirtualAppliance \
  --next-hop-ip-address <leader-internal-ip>

# Associate route table with worker subnet
az network vnet subnet update \
  --resource-group <resource-group> \
  --vnet-name cozystack-vnet \
  --name workers \
  --route-table kilo-routes
```

Add a route for each remote location's subnet (repeat the `route create` command for every on-premises or other cloud subnet that must be reachable through the WireGuard mesh).

{{% alert title="Important" color="warning" %}}
- The `<leader-internal-ip>` is the internal IP of the Kilo location leader in this subnet. In a VMSS-based setup, this is typically the first instance that joins the cluster. You can find it by checking `kilo.squat.ai/leader: "true"` annotation on the nodes.
- IP forwarding must be enabled on the leader's NIC (see Step 4).
- If the leader node changes, the route table must be updated with the new leader's IP.
{{% /alert %}}

## Step 2: Create Talos Image

### 2.1 Generate Schematic ID

Create a schematic at [factory.talos.dev](https://factory.talos.dev) with required extensions:

```bash
curl -s -X POST https://factory.talos.dev/schematics \
  -H "Content-Type: application/json" \
  -d '{
    "customization": {
      "systemExtensions": {
        "officialExtensions": [
          "siderolabs/amd-ucode",
          "siderolabs/amdgpu-firmware",
          "siderolabs/bnx2-bnx2x",
          "siderolabs/drbd",
          "siderolabs/i915-ucode",
          "siderolabs/intel-ice-firmware",
          "siderolabs/intel-ucode",
          "siderolabs/qlogic-firmware",
          "siderolabs/zfs"
        ]
      }
    }
  }'
```

Save the returned `id` as `SCHEMATIC_ID`.

### 2.2 Create Managed Image from VHD

```bash
# Download Talos Azure image
curl -L -o azure-amd64.raw.xz \
  "https://factory.talos.dev/image/${SCHEMATIC_ID}/<talos-version>/azure-amd64.raw.xz"

# Decompress
xz -d azure-amd64.raw.xz

# Convert to VHD
qemu-img convert -f raw -o subformat=fixed,force_size -O vpc \
  azure-amd64.raw azure-amd64.vhd

# Get VHD size
VHD_SIZE=$(stat -f%z azure-amd64.vhd)  # macOS
# VHD_SIZE=$(stat -c%s azure-amd64.vhd)  # Linux

# Create managed disk for upload
az disk create \
  --resource-group <resource-group> \
  --name talos-<talos-version> \
  --location <location> \
  --upload-type Upload \
  --upload-size-bytes $VHD_SIZE \
  --sku Standard_LRS \
  --os-type Linux \
  --hyper-v-generation V2

# Get SAS URL for upload
SAS_URL=$(az disk grant-access \
  --resource-group <resource-group> \
  --name talos-<talos-version> \
  --access-level Write \
  --duration-in-seconds 3600 \
  --query accessSAS --output tsv)

# Upload VHD
azcopy copy azure-amd64.vhd "$SAS_URL" --blob-type PageBlob

# Revoke access
az disk revoke-access \
  --resource-group <resource-group> \
  --name talos-<talos-version>

# Create managed image from disk
az image create \
  --resource-group <resource-group> \
  --name talos-<talos-version> \
  --location <location> \
  --os-type Linux \
  --hyper-v-generation V2 \
  --source $(az disk show --resource-group <resource-group> \
    --name talos-<talos-version> --query id --output tsv)
```

## Step 3: Create Talos Machine Config for Azure

Create a machine config similar to the Hetzner one, with these Azure-specific changes:

```yaml
machine:
  # Kilo annotations for WireGuard mesh (applied automatically on join)
  nodeAnnotations:
    kilo.squat.ai/location: azure
    kilo.squat.ai/persistent-keepalive: "20"
  nodeLabels:
    topology.kubernetes.io/zone: azure
  kubelet:
    nodeIP:
      validSubnets:
        - 10.2.0.0/24                  # Azure VNet subnet
    # Required for external cloud provider (ProviderID assignment)
    extraArgs:
      cloud-provider: external
```

{{% alert title="Note" color="info" %}}
Kilo reads `kilo.squat.ai/location` from **node annotations**, not labels. The `persistent-keepalive` annotation is critical for Azure nodes behind NAT -- it enables WireGuard NAT traversal, allowing Kilo to discover the real public endpoint of the node automatically.
{{% /alert %}}

{{% alert title="Important" color="warning" %}}
The `cloud-provider: external` setting is required for the Azure cloud-controller-manager to assign ProviderID to nodes.
Without it, the cluster-autoscaler cannot match Kubernetes nodes to Azure VMSS instances.
This setting must be present on **all** nodes in the cluster, including control plane nodes.
{{% /alert %}}

All other settings (cluster tokens, control plane endpoint, extensions, etc.) remain the same as the Hetzner config.

## Step 4: Create VMSS (Virtual Machine Scale Set)

```bash
IMAGE_ID=$(az image show \
  --resource-group <resource-group> \
  --name talos-<talos-version> \
  --query id --output tsv)

az vmss create \
  --resource-group <resource-group> \
  --name workers \
  --location <location> \
  --orchestration-mode Uniform \
  --image "$IMAGE_ID" \
  --vm-sku Standard_D2s_v3 \
  --instance-count 0 \
  --vnet-name cozystack-vnet \
  --subnet workers \
  --public-ip-per-vm \
  --custom-data machineconfig-azure.yaml \
  --security-type Standard \
  --admin-username talos \
  --authentication-type ssh \
  --generate-ssh-keys \
  --upgrade-policy-mode Manual

# Enable IP forwarding on VMSS NICs (required for Kilo leader to forward traffic)
az vmss update \
  --resource-group <resource-group> \
  --name workers \
  --set virtualMachineProfile.networkProfile.networkInterfaceConfigurations[0].enableIPForwarding=true
```

{{% alert title="Important" color="warning" %}}
- Must use `--orchestration-mode Uniform` (cluster-autoscaler requires Uniform mode)
- Must use `--public-ip-per-vm` for WireGuard connectivity
- IP forwarding must be enabled on VMSS NICs so the Kilo leader can forward traffic between the WireGuard mesh and non-leader nodes in the same subnet
- Check VM quota in your region: `az vm list-usage --location <location>`
- `--custom-data` passes the Talos machine config to new instances
{{% /alert %}}

## Step 5: Deploy Cluster Autoscaler

Create the Package resource:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cluster-autoscaler-azure
spec:
  variant: default
  components:
    cluster-autoscaler-azure:
      values:
        cluster-autoscaler:
          azureClientID: "<APP_ID>"
          azureClientSecret: "<PASSWORD>"
          azureTenantID: "<TENANT_ID>"
          azureSubscriptionID: "<SUBSCRIPTION_ID>"
          azureResourceGroup: "<RESOURCE_GROUP>"
          azureVMType: "vmss"
          autoscalingGroups:
            - name: workers
              minSize: 0
              maxSize: 10
```

Apply:
```bash
kubectl apply -f package.yaml
```

## Step 6: Kilo WireGuard Connectivity

Azure nodes are behind NAT, so their initial WireGuard endpoint will be a private IP. Kilo handles this automatically through WireGuard's built-in NAT traversal when `persistent-keepalive` is configured (already included in the machine config from Step 3).

The flow works as follows:
1. The Azure node initiates a WireGuard handshake to the on-premises leader (which has a public IP)
2. `persistent-keepalive` sends periodic keepalive packets, maintaining the NAT mapping
3. The on-premises Kilo leader discovers the real public endpoint of the Azure node through WireGuard
4. Kilo stores the discovered endpoint and uses it for subsequent connections

{{% alert title="Note" color="info" %}}
No manual `force-endpoint` annotation is needed. The `kilo.squat.ai/persistent-keepalive: "20"` annotation in the machine config is sufficient for Kilo to discover NAT endpoints automatically. Without this annotation, Kilo's NAT traversal mechanism is disabled and the tunnel will not stabilize.
{{% /alert %}}

## Testing

### Manual scale test

```bash
# Scale up
az vmss scale --resource-group <resource-group> --name workers --new-capacity 1

# Check node joined
kubectl get nodes -o wide

# Check WireGuard tunnel
kubectl logs -n cozy-kilo <kilo-pod-on-azure-node>

# Scale down
az vmss scale --resource-group <resource-group> --name workers --new-capacity 0
```

### Autoscaler test

Deploy a workload to trigger autoscaling:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-azure-autoscale
spec:
  replicas: 3
  selector:
    matchLabels:
      app: test-azure
  template:
    metadata:
      labels:
        app: test-azure
    spec:
      nodeSelector:
        topology.kubernetes.io/zone: azure
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
```

## Troubleshooting

### Node doesn't join cluster
- Check that the Talos machine config control plane endpoint is reachable from Azure
- Verify NSG rules allow outbound traffic to port 6443
- Check VMSS instance provisioning state: `az vmss list-instances --resource-group <resource-group> --name workers`

### WireGuard tunnel not established
- Verify the node has `kilo.squat.ai/persistent-keepalive: "20"` annotation
- Verify the node has `kilo.squat.ai/location: azure` annotation (not just as a label)
- Check NSG allows inbound UDP 51820
- Inspect kilo logs: `kubectl logs -n cozy-kilo <kilo-pod>`
- Check for "WireGuard configurations are different" messages repeating every 30 seconds -- this indicates `persistent-keepalive` annotation is missing

### Non-leader nodes unreachable (kubectl logs/exec timeout)

If `kubectl logs` or `kubectl exec` works for the Kilo leader node but times out for all other nodes in the same Azure subnet:

1. **Verify IP forwarding** is enabled on the VMSS:
   ```bash
   az vmss show --resource-group <resource-group> --name workers \
     --query "virtualMachineProfile.networkProfile.networkInterfaceConfigurations[0].enableIPForwarding"
   ```
   If `false`, enable it and apply to existing instances:
   ```bash
   az vmss update --resource-group <resource-group> --name workers \
     --set virtualMachineProfile.networkProfile.networkInterfaceConfigurations[0].enableIPForwarding=true
   az vmss update-instances --resource-group <resource-group> --name workers --instance-ids "*"
   ```

2. **Verify route table** is associated with the subnet and contains routes for all remote subnets pointing to the leader's IP as a Virtual Appliance (see Step 1.5).

3. **Test the return path** from the leader node:
   ```bash
   # This should work (same subnet, direct)
   kubectl exec -n cozy-kilo <leader-kilo-pod> -- ping -c 2 <non-leader-ip>
   # This tests the return path through the route table
   kubectl exec -n cozy-kilo <leader-kilo-pod> -- ping -c 2 -I <leader-wireguard-ip> <non-leader-ip>
   ```
   If the first ping works but the second fails, the route table is missing or misconfigured.

### VM quota errors
- Check quota: `az vm list-usage --location <location>`
- Request quota increase via Azure portal
- Try a different VM family that has available quota

### SkuNotAvailable errors
- Some VM sizes may have capacity restrictions in certain regions
- Try a different VM size: `az vm list-skus --location <location> --size <prefix>`
