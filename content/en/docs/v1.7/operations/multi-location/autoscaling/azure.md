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
- Existing Talos Kubernetes cluster
- [Networking Mesh]({{% ref "../networking-mesh" %}}) and [Local CCM]({{% ref "../local-ccm" %}}) configured

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

From your cluster repository, generate a worker config file:

```bash
talm template -t templates/worker.yaml --offline --full > nodes/azure.yaml
```

Then edit `nodes/azure.yaml` for Azure workers:

1. Add Azure location metadata (see [Networking Mesh]({{% ref "../networking-mesh" %}})):
   ```yaml
   machine:
     nodeAnnotations:
       kilo.squat.ai/location: azure
       kilo.squat.ai/persistent-keepalive: "20"
     nodeLabels:
       topology.kubernetes.io/zone: azure
   ```
2. Set public Kubernetes API endpoint:
   Change `cluster.controlPlane.endpoint` to the **public** API server address (for example `https://<public-api-ip>:6443`). You can find this address in your kubeconfig or publish it via ingress.
3. Remove discovered installer/network sections:
   Delete `machine.install` and `machine.network` sections from this file.
4. Set external cloud provider for kubelet (see [Local CCM]({{% ref "../local-ccm" %}})):
   ```yaml
   machine:
     kubelet:
       extraArgs:
         cloud-provider: external
   ```
5. Fix node IP subnet detection:
   Set `machine.kubelet.nodeIP.validSubnets` to the actual Azure subnet where autoscaled nodes run (for example `192.168.102.0/23`).
6. (Optional) Add registry mirrors to avoid Docker Hub rate limiting:
   ```yaml
   machine:
     registries:
       mirrors:
         docker.io:
           endpoints:
             - https://mirror.gcr.io
   ```

Result should include at least:

```yaml
machine:
  nodeAnnotations:
    kilo.squat.ai/location: azure
    kilo.squat.ai/persistent-keepalive: "20"
  nodeLabels:
    topology.kubernetes.io/zone: azure
  kubelet:
    nodeIP:
      validSubnets:
        - 192.168.102.0/23             # replace with your Azure workers subnet
    extraArgs:
      cloud-provider: external
  registries:
    mirrors:
      docker.io:
        endpoints:
          - https://mirror.gcr.io
cluster:
  controlPlane:
    endpoint: https://<public-api-ip>:6443
```

All other settings (cluster tokens, CA, extensions, etc.) remain the same as the generated template.

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
  --custom-data nodes/azure.yaml \
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

### Connecting to remote workers for diagnostics

You can debug Azure worker nodes using the **Serial console** in the Azure portal:
navigate to your VMSS instance → **Support + troubleshooting** → **Serial console**.
This gives you direct access to the node's console output without requiring network connectivity.

Alternatively, use `talm dashboard` to connect through the control plane:

```bash
talm dashboard -f nodes/<control-plane>.yaml -n <worker-node-ip>
```

Where `<control-plane>.yaml` is your control plane node config and `<worker-node-ip>` is
the Kubernetes internal IP of the remote worker.

### Node stuck in maintenance mode

If you see the following messages in the serial console:

```
[talos]  talosctl apply-config --insecure --nodes 10.2.0.5 --file <config.yaml>
[talos] or apply configuration using talosctl interactive installer:
[talos]  talosctl apply-config --insecure --nodes 10.2.0.5 --mode=interactive
```

This means the machine config was not picked up or is invalid. Common causes:

- **Unsupported Kubernetes version**: the `kubelet` image version in the config is not compatible with the current Talos version
- **Malformed config**: YAML syntax errors or invalid field values
- **customData not applied**: the VMSS instance was created before the config was updated

To debug, apply the config manually via Talos API (port 50000 must be open in the NSG):

```bash
talosctl apply-config --insecure --nodes <node-public-ip> --file nodes/azure.yaml
```

If the config is rejected, the error message will indicate what needs to be fixed.

To update the machine config for new VMSS instances:

```bash
az vmss update \
  --resource-group <resource-group> \
  --name workers \
  --custom-data @nodes/azure.yaml
```

After updating, delete existing instances so they are recreated with the new config:

```bash
az vmss delete-instances \
  --resource-group <resource-group> \
  --name workers \
  --instance-ids "*"
```

{{% alert title="Warning" color="warning" %}}
Azure does not provide a way to read back the `customData` from a VMSS — you can only set it. Always keep your machine config file (`nodes/azure.yaml`) in version control as the single source of truth.
{{% /alert %}}

### Node doesn't join cluster
- Check that the Talos machine config control plane endpoint is reachable from Azure
- Verify NSG rules allow outbound traffic to port 6443
- Verify NSG rules allow inbound traffic to port 50000 (Talos API) for debugging
- Check VMSS instance provisioning state: `az vmss list-instances --resource-group <resource-group> --name workers`

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

2. **Test the return path** from the leader node:
   ```bash
   # This should work (same subnet, direct)
   kubectl exec -n cozy-kilo <leader-kilo-pod> -- ping -c 2 <non-leader-ip>
   ```

### VM quota errors
- Check quota: `az vm list-usage --location <location>`
- Request quota increase via Azure portal
- Try a different VM family that has available quota

### SkuNotAvailable errors
- Some VM sizes may have capacity restrictions in certain regions
- Try a different VM size: `az vm list-skus --location <location> --size <prefix>`
