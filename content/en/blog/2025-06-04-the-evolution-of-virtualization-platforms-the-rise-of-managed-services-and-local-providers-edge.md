---
title: "The Evolution of Virtualization Platforms: The Rise of Managed Services and Local Providers’ Edge…"
slug: the-evolution-of-virtualization-platforms-the-rise-of-managed-services-and-local-providers-edge-
date: 2025-06-04
author: "Andrei Kvapil"
description: "Hello everyone! I’m Andrey Kvapil, CEO of Ænix and developer of Cozystack, an open-source platform and framework for building cloud…"
---

### The Evolution of Virtualization Platforms: The Rise of Managed Services and Local Providers’ Edge Against Hyperscalers

Hello everyone! I’m Andrey Kvapil, CEO of Ænix and developer of Cozystack, an open-source platform and framework for building cloud infrastructure. In this article, I want to share my perspective on how modern cloud patterns have transformed infrastructure approaches, the evolving role of service providers and public clouds in this landscape, and most importantly, how virtualization’s purpose has fundamentally changed in today’s infrastructure stack.

![](https://cdn-images-1.medium.com/max/800/0*4YRaynfuf5g_fiSY)

### The Core Challenge for Local Service Providers

Modern applications rely on an ever-growing stack of technologies: databases, caches, queues, S3 storage, and more. This complexity increases technical and cognitive operational burden on infrastructure teams. As a result, skilled engineers command premium salaries, making infrastructure maintenance far more expensive than application development itself.

The risks compound with scale. More components mean more potential failure points and a single critical design flaw can stall growth or jeopardize entire systems. Every minute of downtime translates to lost revenue or direct financial impact.

In today’s cloud-dominated world, responsibility for infrastructure increasingly falls on service providers. Businesses now prefer turnkey solutions, shifting focus from low-level operations to core priorities. This drives the migration from IaaS (where clients manage OS, middleware, and runtime) to PaaS where providers not only maintain infrastructure but deliver managed services (databases, message brokers, etc.) as seamlessly as spinning up VMs.

![](https://cdn-images-1.medium.com/max/800/0*mcUODCoqH2xPlnjy)

These shifts have dramatically reshaped virtualization’s purpose. Virtual machines are losing ground to managed services: Kubernetes, databases, caches, queues, and beyond. This inherently advantages cloud platforms like AWS, GCP, and Azure over traditional providers (especially local ones lacking comparable infrastructure). Hyperscalers, with their vast R&D budgets and engineering armies, have already deployed mature PaaS offerings, while resource-constrained local providers often remain stuck offering basic IaaS, perpetually playing catch-up.

So how did we get here? Let’s trace the rise of “as-a-Service” ecosystems and explore actionable strategies for local providers to compete against entrenched tech giants.

### In the Beginning: When Servers Were Pets

Back then, all server workloads ran exclusively on-site. The internet was slow and unreliable, with public services limited to universities and large organizations. Hardware lived in-house, tucked away in company server rooms, meticulously tended by system administrators. Virtual machines didn’t exist yet.

Every server was manually configured to juggle multiple applications simultaneously because process isolation simply wasn’t standard practice. While dedicating an entire server to a single application was technically possible, the idle hardware represented such waste that only major corporations could justify it. Scaling posed even greater challenges.

Every time you needed to deploy something new, you’d follow the same process:

- Buy a physical server that meets your requirements.
- Install the operating system.
- Set up networking.
- Install and configure the application or applications.

And once it was up and running, you continued maintaining it: installing updates, troubleshooting issues, and treating the server like a “pet.” You cared for it, fixed it when it broke, and did everything to keep it alive. This approach worked fine when you had just a few servers. But once the number grew, it became a tedious daily routine.

### The Advent of Virtualization

Virtualization revolutionized infrastructure management, simplifying countless tasks. They allowed us to treat our servers more flexibly. Gone were the days of purchasing new hardware for every server setup — now you could simply allocate resources from your hypervisor and spin up a VM. Hardware failures became less catastrophic as VMs could migrate to other servers. The ability to snapshot and back up entire VMs brought unprecedented convenience.

This gave rise to dedicated virtualization platforms like VMware, Hyper-V, Xen, and Proxmox. Such platforms offered tools to automate deployment, networking, and VM templating. Yet despite these advancements, the fundamental approach to VM usage remained unchanged. You still bore full responsibility for managing each VM’s lifecycle. OS installation typically still involved virtual CD-ROMs, followed by manual configuration or configuration management tools.

Even when streamlining the process through cloning pre-configured images, these virtual servers continued operating as pets. If a VM failed, the application running inside it died with it. This pet model still demanded significant maintenance effort.

While these solutions persist today with enhanced features offering better pet management tools, they remained fundamentally pet-oriented. The industry clearly needed evolution.

### The Shift from Virtualization to Cloud

Hosting companies and cloud providers played a pivotal role in driving the transition to cloud computing. When virtual machines became available in the cloud, many businesses found this model far more advantageous than maintaining their own hardware and support teams.

As customers voted with their wallets, providers rapidly expanded, building reliable data centers with fault-tolerant storage systems and networks. A new class of virtualization platforms emerged, delivering infrastructure as a service (IaaS). Solutions like OpenStack, OpenNebula, and CloudStack revolutionized operations by managing VM fleets through templates, golden images, resource pools, flavors, and instance types.

These next-gen platforms abandoned the “pets” mentality entirely. Instead, they provided users with self-service interfaces for cloud resource consumption. VMs ceased being virtual replicas of physical servers and became mere slices of underlying hardware. Their failure stopped being critical, as cloud-native applications now ran across multiple VMs with built-in fault tolerance.

The paradigm shifted toward full automation, where users could provision any VM on demand. Data migrated outside system disks to persistent volumes and external storage, transforming VMs into disposable compute units delivering CPU and RAM.

Yet one challenge persisted: businesses demanded reproducible infrastructure, fueling the explosive growth of Infrastructure as Code practices.

### Infrastructure as Code

While web interfaces serve well for visualization, engineers consistently prefer working with APIs, which all major cloud platforms like AWS and GCP provide.

Tools like Terraform enable infrastructure as code management, allowing you to define your application requirements and provision identical development, staging, or production environments in seconds. This approach facilitates dynamic feature testing while preventing production surprises. Ansible and other configuration management systems handle OS configuration and software deployment within virtual machines, a pattern that remains popular despite growing business adoption of containerization technologies.

While infrastructure automation challenges were largely solved, the industry shifted focus to a new problem: while we mastered infrastructure creation, the components within it remained manually managed. Beyond declarative infrastructure definitions, significant imperative logic persisted (OS configuration, package installation, and application delivery) typically addressed through Ansible. However, each deployment step carried potential failure points, while businesses increasingly demanded reliable workload deployment reproducibility.

Furthermore, substantial variations between provider APIs created standardization barriers, inevitably leading to vendor lock-in situations.

### Docker and the Rise of Containerization

In many ways, Docker adapted successful cloud patterns and applied them at the operating system level. Instead of installing packages, you could simply take a ready container image and run it as-is with the required parameters. The image would be pulled from a Docker Registry and instantiated as a container, similar to launching a cloud VM from a golden image, but operating at the OS level.

This approach proved so effective that it revolutionized software delivery and execution. Countless applications were containerized, while Docker standardized logging methods, firewall configuration, and taught us to store data outside containers (to prevent data loss). It also established the practice of running separate processes in different containers, adhering to Docker’s philosophy that a container should only serve as a sandbox for a single process.

However, Docker has its limitations . It excels on local systems but falls short when dealing with clustered workloads and managing large numbers of containers. While it solved workload reproducibility, a new challenge emerged: intelligent orchestration at scale, including automated failover and traffic balancing. This is where Kubernetes entered the scene, establishing itself as the new standard for server workload deployment.

### Kubernetes as the Containerization Standard

Kubernetes emerged from within Google and quickly gained backing from major vendors, which propelled it to become the industry standard. Interestingly, its development is primarily driven by those same large cloud providers who needed a tool to help customers utilize cloud services more efficiently.

From the outset, Kubernetes integrated tightly with cloud provider APIs, delivering capabilities like automatic instance provisioning (autoscaling), load balancers, and persistent storage volumes.

![](https://cdn-images-1.medium.com/max/800/0*l1iFAzE2mtxqG8Vw)
Source — [Kubernetes Project Journey Report](https://www.cncf.io/reports/kubernetes-project-journey-report/)

Naturally, many enthusiasts attempted to replicate the success of major cloud providers by running Kubernetes on their own hardware. However, these deployments typically resulted in static clusters lacking the numerous integrations that truly unlock Kubernetes’ potential.

Yet this didn’t stop Kubernetes from building a massive community and successfully popularizing new application design approaches. Ultimately, Kubernetes provides businesses with unified abstractions for working across any cloud supporting managed Kubernetes services, making applications even more cloud-agnostic.

As Kubernetes evolved, it introduced extension mechanisms and expanded support for stateful workloads through operators and CRDs. This unified operations for complex databases and other solutions, encapsulating expert developer knowledge within these operators. Users now interact with high-level abstractions like Postgres clusters, Redis, or RabbitMQ, while specialized operators handle the underlying logic.

However, these operators require a fully-featured Kubernetes environment with ingress load balancing, persistent volumes, and autoscaling — features that strongly tie users to public clouds. Recreating this functionality on private infrastructure remains challenging today. Cloud providers recognize this advantage and actively promote their managed services as turnkey solutions.

### Platforms and the Future of Local Providers

The cloud-native approach has fundamentally transformed how we build modern applications and their underlying systems. Rather than keeping all eggs in one basket, we now rigorously separate responsibilities. Cloud platforms handle increasingly more routine tasks, allowing developers to focus on what truly matters — application business logic.

Cloud platforms have evolved to provide abstractions for nearly everything. Beyond virtual machines, they now offer managed services like Kubernetes clusters, databases, caches, message queues, and S3 storage — all considered essential infrastructure components today.

Cloud provider selection increasingly depends on the breadth of managed services they can operate. The key insight? End users want to consume infrastructure, not operate it.

Hyperscalers led this transition by rapidly integrating Kubernetes into their platforms and monetizing business needs through managed Kubernetes and other services. Local providers again found themselves playing catch-up: building a Kubernetes-based cloud platform demands not just substantial investment but deep technical expertise.

Until recently, no open-source standard existed for delivering managed services at scale. This is precisely the challenge we’re addressing at Ænix through Cozystack — a free platform we’ve contributed to CNCF to ensure permanent open-source availability.

Cozystack functions as a next-gen hypervisor/cloud platform, enabling local providers to offer not just VMs but full-fledged managed services on their own hardware with single-click simplicity. Built entirely on Kubernetes and CNCF-hosted solutions, it meets modern providers’ needs for true managed services using battle-tested cloud-native components.

As an open CNCF project (home to Kubernetes, Cilium, Flux etc.), Cozystack helps providers embrace digital sovereignty, improve margins, and eliminate vendor lock-in while accelerating time-to-market for profitable cloud services — including GPU-powered AI workloads.

![](https://cdn-images-1.medium.com/max/800/0*FQtHSkPsUADeGJZv)

### Conclusion

The world of cloud technologies is evolving at breakneck speed, and in this new era, those who adapt quickly will thrive. Hyperscalers long ago bet on automation and abstractions that free businesses from infrastructure concerns. Now local providers have this same opportunity.

Cozystack is our answer to this pivotal moment. More than just a technological platform, it’s an equalizer that lets service providers compete with global leaders. We believe the future belongs to open, transparent solutions built on proven cloud-native principles. And we invite you to help build that future.

Join our community, develop your own managed services, and together we’ll make cloud technology accessible, sovereign, and equitable — for everyone.

### Additional materials

**Articles**

- [DIY: Create Your Own Cloud with Kubernetes](https://kubernetes.io/blog/2024/04/05/diy-create-your-own-cloud-with-kubernetes-part-1/)
- [How we built a dynamic Kubernetes API Server for the API Aggregation Layer in Cozystack](https://kubernetes.io/blog/2024/11/21/dynamic-kubernetes-api-server-for-cozystack/)
- [Cozystack Becomes a CNCF Sandbox Project](https://blog.aenix.io/cozystack-becomes-a-cncf-sandbox-project-3702b8906971)
- [Cozystack Recognized in CNCF’s CNAI Landscape](https://blog.aenix.io/cozystack-recognized-in-cncfs-cnai-landscape-331f892b9639)

**Videos**

- [Journey to Stable Infrastructures with Talos Linux &amp; Cozystack | Andrei Kvapil | SREday London 2024](https://www.youtube.com/watch?v=uhXujtTzG44)
- [Talos Linux: You don’t need an operating system, you only need Kubernetes / Andrei Kvapil](https://www.youtube.com/watch?v=9CIMTum9bTA)
- [Comparing GitOps: Argo CD vs Flux CD, with Andrei Kvapil | KubeFM](https://www.youtube.com/watch?v=4RVe32xRITo)
- [Cozystack on Talos Linux](https://www.youtube.com/watch?v=s79VqXu-eG4)
- [GPU-Powered AI on VMs, Kubernetes &amp; Bare Metal with Cozystack](https://www.youtube.com/watch?v=slQxsj6Oj4M)
- [Kubernetes is the new Skynet or the rise of Kubernetes automation: CNCF webinar](https://www.youtube.com/watch?v=9LSwnr31t7Y)

### Join Cozystack Community

- [Telegram](https://t.me/cozystack)
- [Slack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (in [Kubernetes Slack workspace](https://communityinviter.com/apps/kubernetes/community))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)