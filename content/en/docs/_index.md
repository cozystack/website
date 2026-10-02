---
title: "Choose Documentation Version"
linkTitle: "Documentation"
description: "Select the version of Cozystack documentation that matches your installation"
layout: docs-landing
weight: 40
cascade:
  type: docs
# The navbar "Documentation" item is defined in hugo.yaml `menus.main` (not here)
# so it renders on every language. A page-front-matter menu entry only appears on
# languages where this page exists, which dropped the link on translated pages.
---

### Check Your Current Version

If you have an existing installation, run:

```bash
kubectl get deployment -n cozy-system
```

- **v1.x:** You will see a `cozystack-operator` deployment.
- **v0:** You will see a `cozystack` deployment (the legacy installer).

**Additional Resources:**
- [Release notes](https://github.com/cozystack/cozystack/releases)
