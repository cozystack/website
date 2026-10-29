---
title: "Troubleshooting LINSTOR controller crash loops"
linkTitle: "LINSTOR: controller problems"
description: "Explains how to resolve LINSTOR controller problems."
weight: 100
---

## Restarting the controller

If the controller is running but appears idle/unresponsive, try restarting it.
This operation is idempotent and safe: pending (unfinished) work will resume after the restart.


## LINSTOR controller crash loop

If linstor-controller can't start, but logs do not contain any useful information, you can increase the log level
(maximum level is `TRACE`).

Example of `LINSTORCluster` CR with increased log level:

```yaml
apiVersion: piraeus.io/v1
kind: LINSTORCluster
spec:
  controller:
    podTemplate:
      spec:
        containers:
          - name: linstor-controller
            env:
              # both settings are used by linstor-controller
              - name: LS_LOG_LEVEL
                value: TRACE
              - name: LS_LOG_LEVEL_LINSTOR
                value: TRACE
```

Note: if linstor-controller is not in a crash loop, but you need to increase log level,
you can do so *temporarily* in the runtime using the following command:

```bash
linstor controller set-log-level --global TRACE
```

This setting will be reset to initial value when the controller restarts.


## LINSTOR plays dead after certificate expiration

If you had configured LINSTOR with internal TLS communication, certificates will be created and rotated automatically.
But there is an open issue [piraeusdatastore/piraeus-operator#701](https://github.com/piraeusdatastore/piraeus-operator/issues/701)
about components not picking up new certificates after rotation.
The workaround is to restart all LINSTOR components manually.

Follow these steps in order:

1.  Restart the `linstor-controller`.
2.  Restart each satellite one by one. Do not restart them all at once.
    After each satellite restart, check its logs for errors before proceeding to the next one.
3.  Restart the `linstor-controller` again.
    This is necessary because the controller also initiates connections to satellites and may not automatically reconnect
    to a satellite that has been restarted.
4.  Restart all remaining LINSTOR components.