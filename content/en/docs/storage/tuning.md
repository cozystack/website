---
title: "Tuning DRBD Resync Controller in LINSTOR"
linkTitle: "Tuning"
description: "Learn how to tune DRBD resync controller parameters in LINSTOR for faster synchronization"
weight: 110
aliases:
---

Cozystack administrators can adjust DRBD synchronization performance by setting tuning parameters
for the LINSTOR Controller.

This allows you to optimize the speed of resynchronization without overloading the replication network or storage backend.

For detailed explanations of all available parameters and tuning recommendations, please refer to the official LINBIT guide:
[Tuning the DRBD Resync Controller](https://kb.linbit.com/drbd/tuning-the-drbd-resync-controller/).

## Example: Recommended Settings for 10G Networks

We consider the following values to be optimal for clusters connected with a 10-Gigabit network:

```bash
linstor c sp DrbdOptions/Net/max-buffers          36864
linstor c sp DrbdOptions/Net/rcvbuf-size          10485760
linstor c sp DrbdOptions/Net/sndbuf-size          10485760
linstor c sp DrbdOptions/PeerDevice/c-fill-target 2048
linstor c sp DrbdOptions/PeerDevice/c-max-rate    737280
linstor c sp DrbdOptions/PeerDevice/c-min-rate    245760
linstor c sp DrbdOptions/PeerDevice/resync-rate   245760
linstor c sp DrbdOptions/PeerDevice/c-plan-ahead  10
```

- `c-max-rate` should match the maximum sustained throughput of your disks or the network throughput (whichever is lower).
- `c-min-rate` and `resync-rate` should be set to roughly one third of `c-max-rate`.
