---
title: "Представляем /cozystack:wizard — управляемый установщик Cozystack"
slug: introducing-cozystack-wizard
date: 2026-05-19
author: "Timur Tukaev"
description: "/cozystack:wizard — новый управляемый установщик, который оркестрирует полное развёртывание Cozystack от начала до конца на Talos, Ubuntu и существующих кластерах, разбираясь с ловушками cert-SAN в NAT-облаках, провижинингом ZFS, гонками регистрации LINSTOR и не только."
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

![Мастер Cozystack](cozystack-wizard.png)

Мы выпустили **`/cozystack:wizard`** — управляемый установщик Cozystack.

Укажите ему `Talos`, `Ubuntu` или `Existing` — и он оркестрирует всю цепочку от начала до конца. Он разбирается с ловушками cert-SAN в NAT-облаках (OCI, GCP, AWS), провижинингом ZFS на Talos, гонками регистрации LINSTOR и десятком других ловушек, на которые мы натыкались при реальных установках.

Boot-to-Talos тоже работает: если узлы уже подняты на базовом Talos, мастер обновляет их до образа, настроенного под Cozystack. Сквозной сценарий проверен на кластере Talos из 3 узлов в OCI.

## Breaking change: консолидация плагинов

Мы объединили пять плагинов в два — `cozystack` и `linstor` — и переименовали скиллы. Если у вас были старые плагины, удалите прежние и переустановите:

```bash
/plugin install cozystack@cozystack-claude-plugins
/plugin install linstor@cozystack-claude-plugins
```

Затем запустите:

```bash
/cozystack:wizard
```

## Попробуйте и пришлите отзыв

Мастер призван провести вас от свежего набора узлов (или существующего кластера) до работающего Cozystack без ручной возни с длинным хвостом крайних случаев. Мы стресс-тестировали его на конфигурациях выше, но чем больше окружений он увидит, тем лучше становится.

Пожалуйста, попробуйте его и расскажите нам, что сработало, что сломалось и что вызвало затруднения.

---

## Присоединяйтесь к сообществу

- GitHub: [github.com/cozystack/cozystack](https://github.com/cozystack/cozystack)
- Сообщество в Telegram: [t.me/cozystack](https://t.me/cozystack/)
- Cozystack в Kubernetes Slack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (нужно приглашение? [slack.kubernetes.io](https://slack.kubernetes.io))
- Календарь встреч сообщества: [cozystack.io/community](https://cozystack.io/community/)
