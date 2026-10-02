---
title: "दस्तावेज़ीकरण संस्करण चुनें"
linkTitle: "दस्तावेज़ीकरण"
description: "अपनी इंस्टॉलेशन से मेल खाने वाला Cozystack दस्तावेज़ीकरण संस्करण चुनें"
layout: docs-landing
weight: 40
cascade:
  type: docs
source_digest: "sha256:ad7b96ee67d861c7cb4cfb114249228496517c4d942370ca59d377453dbb119a"
translation_status: current
l10n: mt
---

### अपना मौजूदा संस्करण जाँचें

यदि आपके पास पहले से इंस्टॉलेशन है, तो चलाएँ:

```bash
kubectl get deployment -n cozy-system
```

- **v1.x:** आपको `cozystack-operator` डिप्लॉयमेंट दिखाई देगा।
- **v0:** आपको `cozystack` डिप्लॉयमेंट दिखाई देगा (पुराना इंस्टॉलर)।

**अतिरिक्त संसाधन:**
- [रिलीज़ नोट्स](https://github.com/cozystack/cozystack/releases)
