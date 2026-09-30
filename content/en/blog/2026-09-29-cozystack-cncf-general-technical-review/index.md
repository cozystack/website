---
title: "Cozystack Completes the CNCF General Technical Review"
slug: cozystack-cncf-general-technical-review
date: 2026-09-29
author: "Timur Tukaev"
description: "Cozystack has completed the CNCF General Technical Review for incubation, with overhead, load and upgrade behaviour measured on a reference bench and the open gaps listed plainly."
images:
  - "gtr.png"
article_types:
  - news
topics:
  - platform
  - community
  - security
---

{{< figure src="gtr.png" alt="Cozystack completes the CNCF General Technical Review — reference bench results" width="720" >}}

Cozystack has completed the CNCF General Technical Review, the technical half of the due
diligence for moving from Sandbox to Incubation. The snapshot is filed with the CNCF Technical
Oversight Committee in [cncf/toc#2305](https://github.com/cncf/toc/pull/2305), and the living
document is kept in the repository as
[`GENERAL_TECHNICAL_REVIEW.md`](https://github.com/cozystack/cozystack/blob/main/GENERAL_TECHNICAL_REVIEW.md).

The review asks what an operator asks before trusting a platform in production — how it is
installed, upgraded and rolled back, what it costs to run, how it fails, and how security
issues are handled — across Day 0 planning, Day 1 installation and Day 2 operations.

Questions about overhead and scale were answered by measurement, on three servers with
32 vCPU and 128 GB each:

- the idle platform takes about one CPU core and 19 GiB of memory across all three nodes;
- 71 managed PostgreSQL instances with replicated volumes ran with no failures;
- a mixed load of about 76 applications and 402 pods reached Ready without hitting a compute,
  memory or storage ceiling;
- an upgrade converged in about three minutes, a downgrade in about four, and every
  replicated volume survived all four version changes.

The review also records what is still missing, including image signing, a published API
stability policy and an aggregate `NOTICE` file. Each gap is tracked in the open.

A summary of the review, with the measurements and the open items, is on the
[General Technical Review](/compliance/general-technical-review/) page.

## Join the community

- [Cozystack on GitHub](https://github.com/cozystack/cozystack)
- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
