---
title: "Dokumentationsversion wählen"
linkTitle: "Dokumentation"
description: "Wählen Sie die Cozystack-Dokumentation passend zu Ihrer Installation"
layout: docs-landing
weight: 40
cascade:
  type: docs
source_digest: "sha256:ad7b96ee67d861c7cb4cfb114249228496517c4d942370ca59d377453dbb119a"
translation_status: current
l10n: mt
---

### Ihre aktuelle Version ermitteln

Wenn bereits eine Installation vorhanden ist, führen Sie aus:

```bash
kubectl get deployment -n cozy-system
```

- **v1.x:** Sie sehen ein `cozystack-operator`-Deployment.
- **v0:** Sie sehen ein `cozystack`-Deployment (der alte Installer).

**Weitere Ressourcen:**
- [Release Notes](https://github.com/cozystack/cozystack/releases)
