---
title: "Выбор версии документации"
linkTitle: "Документация"
description: "Выберите версию документации Cozystack, соответствующую вашей установке"
layout: docs-landing
weight: 40
cascade:
  type: docs
source_digest: "sha256:ad7b96ee67d861c7cb4cfb114249228496517c4d942370ca59d377453dbb119a"
translation_status: current
l10n: mt
---

### Как узнать текущую версию

Если у вас уже есть установка, выполните:

```bash
kubectl get deployment -n cozy-system
```

- **v1.x:** вы увидите деплоймент `cozystack-operator`.
- **v0:** вы увидите деплоймент `cozystack` (устаревший установщик).

**Дополнительные материалы:**
- [Release notes](https://github.com/cozystack/cozystack/releases)
