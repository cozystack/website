---
title: "Choose Documentation Version"
linkTitle: "Documentation"
description: "Select the version of Cozystack documentation that matches your installation"
weight: 40
cascade:
  type: docs
menu:
  main:
    weight: 40
---

**New users:** Start with [v1 documentation](/docs/v1/) — the current stable release.

**Existing v0.4x users:** Continue with [v0 documentation](/docs/v0/) until you're ready to [upgrade](/docs/v1/operations/upgrades/).

### Check Your Current Version

If you have an existing installation, run:

```bash
kubectl get deployment -n cozy-system
```

- **v1:** You will see a `cozystack-operator` deployment.
- **v0:** You will see a `cozystack` deployment (the legacy installer).
- **Namespace not found:** Cozystack is not installed — start with [v1](/docs/v1/).

**Additional Resources:**
- [Release notes](https://github.com/cozystack/cozystack/releases)
- [v0 to v1 upgrade guide](/docs/v1/operations/upgrades/)
