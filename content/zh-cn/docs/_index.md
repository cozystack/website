---
title: "选择文档版本"
linkTitle: "文档"
description: "选择与您的安装相匹配的 Cozystack 文档版本"
layout: docs-landing
weight: 40
cascade:
  type: docs
source_digest: "sha256:ad7b96ee67d861c7cb4cfb114249228496517c4d942370ca59d377453dbb119a"
translation_status: current
l10n: mt
---

### 查看当前版本

如果您已有安装，请运行：

```bash
kubectl get deployment -n cozy-system
```

- **v1.x：** 您会看到 `cozystack-operator` 部署。
- **v0：** 您会看到 `cozystack` 部署（旧版安装程序）。

**更多资源：**
- [版本发布说明](https://github.com/cozystack/cozystack/releases)
