---
title: "Troubleshooting Piraeus custom resources"
linkTitle: "Piraeus: custom resources got stuck"
description: "Explains how to resolve issues with stuck Piraeus custom resources."
weight: 150
---

## Introduction

Piraeus custom resources are the following:

* `LinstorCluster`
* `LinstorSatellite`
* `LinstorSatelliteConfiguration`
* `LinstorNodeConnection`

The Piraeus controller protects these resources from unintended changes and deletion.
When you delete the resource, controller will first make sure that all downstream resources are deleted.

But the default setting of the webhook is to reject any changes if something goes wrong with the webhook itself.
And, in a disturbed system, webhook may go down a lot, without useful stacktraces.

## Disabling webhook

If you are fixing the CRs and they are "not editable", you need to disable the webhook and maybe operator itself too.

A couple of useful ways how to disable the webhook:

-   If you have a GitOps system that manages piraeus installation, you can stop it for this release and just delete the
    webhook configuration.
    When you unpause the GitOps system, it will recreate the webhook configuration.
-   If you don't want to delete the webhook configuration as it was installed manually, you can "break" its selector.

Example:

```bash
kubectl edit validatingwebhookconfigurations/piraeus-operator-validating-webhook-configuration
```

In the editor, replace all `- linstor*` with `- xlinstor`.
When you are finished, revert the configuration the same way: 
Example Vim commands are: `%s/- linstor/- xlinstor/g` and `%s/- xlinstor/- linstor/g`.

Note: do not disable the webhook permanently. It's there for a reason.

## Disabling controller

The Piraeus controller not only watches its own CRs, it also updates them when necessary.
In most cases you should disable it as well.
Notably, in continuously reconstructs `LinstorSatellite` from `LinstorSatelliteConfiguration`
continuously.

To disable the controller, scale its deployment to zero:

```bash
kubectl -n storage scale deployment piraeus-operator-controller-manager --replicas=0
``` 

When you finish maintenance, scale it back to one replica:

```bash
kubectl -n storage scale deployment piraeus-operator-controller-manager --replicas=1
```

## Drop finalizers

Each Piraeus CR has a finalizer that obviously does not work anyway since you disabled the controller.
If you are going to delete the CR, you need to remove the finalizers section as usual.
