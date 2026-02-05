---
title: Troubleshooting Kubernetes Installation
linkTitle: Troubleshooting
description: "Instructions for resolving typical problems that can occur when installing Kubernetes with `talm`, `talos-bootstrap`, or `talosctl`."
weight: 40
aliases:
---

This page has instructions for resolving typical problems that can occur when installing Kubernetes with `talm`, `talos-bootstrap`, or `talosctl`.

## No Talos nodes in maintenance mode found!

If you encounter issues with the `talos-bootstrap` script not detecting any nodes, follow these steps to diagnose and resolve the issue:

1.  Verify Network Segment

    Ensure that you are running the script within the same network segment as the nodes. This is crucial for the script to be able to communicate with the nodes.

1.  Use Nmap to Discover Nodes

    Check if `nmap` can discover your node by running the following command:

    ```bash
    nmap -Pn -n -p 50000 192.168.0.0/24
    ```
    
    This command scans for nodes in the network that are listening on port `50000`.
    The output should list all the nodes in the network segment that are listening on this port, indicating that they are reachable.

1.  Verify talosctl Connectivity

    Next, verify that `talosctl` can connect to a specific node, especially if the node is in maintenance mode:
    
    ```bash
    talosctl -e "${node}" -n "${node}" get machinestatus -i
    ```
    
    Receiving an error like the following usually means your local `talosctl` binary is outdated:
    
    ```console
    rpc error: code = Unimplemented desc = unknown service resource.ResourceService
    ```
    
    Updating `talosctl` to the latest version should resolve this issue.

1.  Run talos-bootstrap in debug mode

    If the previous steps don’t help, run `talos-bootstrap` in debug mode to gain more insight.
    
    Execute the script with the `-x` option to enable debug mode:
    
    ```bash
    bash -x talos-bootstrap
    ```
    
    Pay attention to the last command displayed before the error; it often indicates the command that failed and can provide clues for further troubleshooting.

# fix ext-lldpd on talos nodes
Waiting a runtime service in talos cause it to stay on booting in talos console, if you want to use lldpd you can patch the nodes,
proceed if you have connectivity with `talosctl`
```bash
cat > lldpd.patch.yaml <<EOF
apiVersion: v1alpha1
kind: ExtensionServiceConfig
name: lldpd
configFiles:
  - content: |
      configure lldp status disabled
    mountPath: /usr/local/etc/lldp/lldpd.conf
EOF
```
To apply the patch to a specific node, run:
```bash
talosctl patch mc -p @lldpd.patch.yaml -n <node> -e <node>
```

Verify which nodes have lldpd installed
```bash
node_net='192.168.100.0/24'
nmap -Pn -n -T4 -p50000 --open -oG - $node_net  | awk '/50000\/open/ { system("talosctl get extensions -n "$2" -e "$2" | grep lldpd") }'
```

If you want to patch all nodes:
```bash
nmap -Pn -n -T4 -p50000 --open -oG - $node_net  | awk '/50000\/open/ {print "talosctl patch mc -p @lldpd.patch.yaml -n "$2" -e "$2" "}'
```

Verify state on talos console
```bash
talosctl dashboard -n $(nmap -Pn -n -T4 -p50000 --open -oG - $node_net | awk '/50000\/open/ {print $2}' | paste -sd,)
```