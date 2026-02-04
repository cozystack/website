---
title: "Upgrades"
linkTitle: "Upgrades"
description: "Upgrade guides"
weight: 1
---

## Upgrading to v1.0

Version 1.0 brings major change to Cozystack control-plane: it is now completely modular and is composed of independent packages.  
To manage packages a cozystack-operator was introduced, which replaces previous installer.  
Assets server is now replaced with a single oci image, and it could be replaced with a git repository if needed.  

However, underlying entities are still helm releases made of helm charts, so during an upgrade no workloads would be recreated or affected in any way.  

### 1. Prerequisites
Along with version 1.0 new management tools were introduced: `cozyhr` and `cozypkg`. You will need their latest versions to proceed with the upgrade.
- Take `cozypkg` from the Cozystack Releases page: https://github.com/cozystack/cozystack/releases
- Take `cozyhr` from its repository: https://github.com/cozystack/cozyhr/releases  
You will also need regular tools such as flux, jq, kubectl, and such.

### 2. Upgrade
- Upgrade to the most recent v0.4x version, such as v0.41.5
- Apply `cozystack-crds.yaml` from the Cozystack Releases page, it contains definitions for new custom resources, such as Package and PackageSource.
- Apply `cozystack-operator.yaml` from the Cozystack Releases page, it will bring cozystack operator to the cluster.
- Generate and apply the main package for your installation with the `/hack/migrate-to-version-1.0.sh` script from the Cozystack repository.
  It will gather values from existing configmaps in the `cozy-system` namespace, and assemble a `Package` resource with all the values.

As soon as the Package is applied, the operator will start migrations and upgrades automatically.
Migrations will clean up legacy components (old installer, assets-server, and obsolete HelmReleases).
You can track the progress by checking `HelmRelease` statuses with `kubectl get hr -A`.

And that's it!
