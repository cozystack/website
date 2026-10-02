---
title: "/cozystack:wizard का परिचय — एक गाइडेड Cozystack इंस्टॉलर"
slug: introducing-cozystack-wizard
date: 2026-05-19
author: "Timur Tukaev"
description: "/cozystack:wizard एक नया गाइडेड इंस्टॉलर है जो Talos, Ubuntu और मौजूदा क्लस्टरों पर पूरे Cozystack परिनियोजन को एंड-टू-एंड ऑर्केस्ट्रेट करता है — NAT वाले क्लाउड में cert-SAN की समस्याओं, ZFS प्रोविज़निंग, LINSTOR रजिस्ट्रेशन रेस और बहुत कुछ संभालते हुए।"
images:
  - "cozystack-wizard.png"
article_types:
  - announcement
topics:
  - platform
  - install
source_digest: "sha256:6f37e3e12783a4e331d4df3ee4ad46b966b2916d69d0598b0c140733f4b58a41"
translation_status: current
l10n: transcreate
---

![Cozystack विज़ार्ड](cozystack-wizard.png)

हमने **`/cozystack:wizard`** जारी किया है — एक गाइडेड Cozystack इंस्टॉलर।

इसे `Talos`, `Ubuntu` या `Existing` बताइए, और यह पूरी श्रृंखला को एंड-टू-एंड ऑर्केस्ट्रेट कर देता है। यह NAT वाले क्लाउड (OCI, GCP, AWS) में cert-SAN की समस्याओं, Talos पर ZFS प्रोविज़निंग, LINSTOR रजिस्ट्रेशन रेस, और एक दर्जन अन्य ऐसी समस्याओं को संभालता है जो वास्तविक इंस्टॉल परीक्षण के दौरान हमें परेशान करती रहीं।

Boot-to-Talos भी काम करता है: अगर नोड पहले से बेस Talos पर चालू हैं, तो विज़ार्ड उन्हें Cozystack-ट्यून्ड इमेज में अपग्रेड कर देता है। एंड-टू-एंड पथ को OCI पर एक 3-नोड Talos क्लस्टर पर सत्यापित किया गया है।

## Breaking change: प्लगइन समेकन

हमने पाँच प्लगइन को दो में समेकित किया है — `cozystack` और `linstor` — और स्किल्स का नाम बदल दिया है। अगर आपके पास पुराने प्लगइन थे, तो पहले वाले अनइंस्टॉल करें और दोबारा इंस्टॉल करें:

```bash
/plugin install cozystack@cozystack-claude-plugins
/plugin install linstor@cozystack-claude-plugins
```

फिर चलाएँ:

```bash
/cozystack:wizard
```

## आज़माएँ और प्रतिक्रिया भेजें

विज़ार्ड का उद्देश्य आपको नोड के एक नए सेट (या किसी मौजूदा क्लस्टर) से एक चलते हुए Cozystack तक ले जाना है, बिना एज-केस की लंबी श्रृंखला का मैन्युअल रूप से पीछा किए। हमने इसे ऊपर दिए गए कॉन्फ़िगरेशन पर स्ट्रेस-टेस्ट किया है, लेकिन यह जितने अधिक एनवायरनमेंट देखेगा, उतना ही बेहतर होता जाएगा।

कृपया इसे आज़माएँ और हमें बताएँ कि क्या काम आया, क्या टूटा, और क्या भ्रमित करने वाला रहा।

---

## समुदाय से जुड़ें

- GitHub: [github.com/cozystack/cozystack](https://github.com/cozystack/cozystack)
- Telegram समुदाय: [t.me/cozystack](https://t.me/cozystack/)
- Kubernetes Slack में Cozystack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (आमंत्रण चाहिए? [slack.kubernetes.io](https://slack.kubernetes.io))
- समुदाय मीटिंग कैलेंडर: [cozystack.io/community](https://cozystack.io/community/)
