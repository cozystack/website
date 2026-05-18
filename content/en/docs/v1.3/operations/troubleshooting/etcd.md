---
title: "Troubleshooting etcd"
linkTitle: "etcd"
description: "Explains how to resolve etcd problems and errors."
weight: 10
---


## How to clean up etcd state

To flush the etcd state from a node, you can use `talm` or `talosctl` with the following commands:

{{< tabs name="etcd reset tools" >}}
{{% tab name="Talm" %}}

Replace `nodeN` with the name of the failed node, for instance, `node0.yaml`:

```bash
talm reset -f nodes/nodeN.yaml --system-labels-to-wipe=EPHEMERAL --graceful=false --reboot
```

{{% /tab %}}

{{% tab name="talosctl" %}}
```bash
talosctl reset --system-labels-to-wipe=EPHEMERAL --graceful=false --reboot
```

{{% /tab %}}
{{< /tabs >}}

{{% alert color="warning" %}}
:warning: This command will remove the state from the specified node. Use it with caution.
{{% /alert %}}
