---
title: "Configuring DRBD Resync Controller in LINSTOR"
linkTitle: "Configuring DRBD"
description: "Learn how to tune DRBD resync controller parameters in LINSTOR for faster synchronization"
weight: 20
---

Cozystack administrators can adjust DRBD synchronization performance by setting tuning parameters
for the LINSTOR Controller.

This allows you to optimize the speed of resynchronization without overloading the replication network or storage backend.

For detailed explanations of all available parameters and tuning recommendations, please refer to the official LINBIT guide:
[Tuning the DRBD Resync Controller](https://kb.linbit.com/drbd/tuning-the-drbd-resync-controller/).

For a multi-datacenter setup, also read the [Multi-DC DRBD configuration]({{% ref "/docs/operations/stretched/drbd-tuning" %}}).

## Recommended Settings for 10G Networks

We consider the following values to be optimal for clusters connected with a 10-Gigabit network:

```bash
linstor controller set-property DrbdOptions/Net/max-buffers          36864
linstor controller set-property DrbdOptions/Net/rcvbuf-size          10485760
linstor controller set-property DrbdOptions/Net/sndbuf-size          10485760
linstor controller set-property DrbdOptions/PeerDevice/c-fill-target 2048
linstor controller set-property DrbdOptions/PeerDevice/c-max-rate    737280
linstor controller set-property DrbdOptions/PeerDevice/c-min-rate    245760
linstor controller set-property DrbdOptions/PeerDevice/resync-rate   245760
linstor controller set-property DrbdOptions/PeerDevice/c-plan-ahead  10
```

-   `c-max-rate` is specified in KiB/s and should match the maximum sustained throughput of your disks or the network throughput (whichever is lower).
    The example value of `737280` corresponds to 720 MiB/s.  
-   `c-min-rate` and `resync-rate` are also in KiB/s and should be set to roughly one third of `c-max-rate`.
