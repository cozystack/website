---
title: "Introducing /cozystack:wizard — a Guided Cozystack Installer"
slug: introducing-cozystack-wizard
date: 2026-05-19
author: "Timur Tukaev"
description: "/cozystack:wizard is a new guided installer that orchestrates a full Cozystack deployment end-to-end across Talos, Ubuntu, and existing clusters — handling cert-SAN traps on NAT'd clouds, ZFS provisioning, LINSTOR registration races, and more."
images:
  - "cozystack-wizard.png"
article_types:
  - announcement
topics:
  - platform
  - install
---

![Cozystack wizard](cozystack-wizard.png)

We've shipped **`/cozystack:wizard`** — a guided Cozystack installer.

Tell it `Talos`, `Ubuntu`, or `Existing`, and it orchestrates the whole chain end-to-end. It handles cert-SAN traps on NAT'd clouds (OCI, GCP, AWS), ZFS provisioning on Talos, LINSTOR registration races, and a dozen other traps that bit us during real-install testing.

Boot-to-Talos works too: if nodes already came up on base Talos, the wizard upgrades them to the Cozystack-tuned image. The end-to-end path is validated on a 3-node OCI Talos cluster.

## Breaking change: plugin consolidation

We have consolidated five plugins into two — `cozystack` and `linstor` — and renamed the skills. If you had the old plugins, uninstall the previous ones and reinstall:

```bash
/plugin install cozystack@cozystack-claude-plugins
/plugin install linstor@cozystack-claude-plugins
```

Then run:

```bash
/cozystack:wizard
```

## Try it and send feedback

The wizard is meant to take you from a fresh set of nodes (or an existing cluster) to a running Cozystack without manually chasing the long tail of edge cases. We've stress-tested it on the configurations above, but the more environments it sees, the better it gets.

Please try it out and let us know what worked, what broke, and what was confusing.

---

## Join the community

- GitHub: [github.com/cozystack/cozystack](https://github.com/cozystack/cozystack)
- Telegram community: [t.me/cozystack](https://t.me/cozystack/)
- Cozystack in Kubernetes Slack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (need an invite? [slack.kubernetes.io](https://slack.kubernetes.io))
- Community Meeting Calendar: [cozystack.io/community](https://cozystack.io/community/)
