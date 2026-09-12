---
title: "Cozystack：基于 Kubernetes 的免费云平台"
description: >
  将一组裸金属服务器变成智能系统，通过简单的 REST API 轻松创建 Kubernetes 集群、数据库即服务、虚拟机、负载均衡器、HTTP 缓存服务以及其他服务。

  使用 Cozystack 构建你自己的云，或提供高性价比的开发环境。
seo:
  title: "Cozystack — 基于 Kubernetes 的开源私有云"
  description: "基于 Kubernetes 的开源云平台，提供托管虚拟机、数据库、S3 存储和 GPU 工作负载。CNCF Sandbox 项目。"
  keywords: ["私有云", "Kubernetes", "开源云平台", "托管 Kubernetes"]
source_digest: "sha256:a2c1ceac912173c93b372da28e9e1410506ac63b14b972e7dc3c2f943d98823e"
translation_status: current
l10n: transcreate
taglines:
  - AWS 的自托管替代方案
  - 面向 AI 的基础设施
  - 开源 VMware 替代方案
use_cases:
  - title: 主机与云服务商
    situation: "你在卖 VPS，而客户如今要的是托管 Kubernetes、数据库和对象存储；每项服务都自己从头做，是一份永远做不完的路线图。"
    outcome: "一个平台，把你现有的硬件变成一份服务目录：租户彼此隔离、自助开通，以及一套计费系统可以直接对接的 Kubernetes 原生 API。"
    link: /docs/guides/use-cases/public-cloud/
    link_text: 构建公有云
  - title: 正在离开 VMware 的团队
    situation: "永久许可证已经没有了，续订配额也来了，而那些虚拟机仍然要跑在你自己能掌控的地方。"
    outcome: "虚拟机和容器运行在同一个集群、你自己的服务器上，具备热迁移与复制存储——迁移是一个工具，而不是一次重写。"
    link: /docs/guides/use-cases/private-cloud/
    link_text: 构建私有云
  - title: 平台团队
    situation: "开发者为一个数据库、一个集群或一套环境提交工单，而平台团队成了这一切的瓶颈。"
    outcome: "开发者像申请 Kubernetes 资源一样提出需求，几分钟内就能拿到——在你设定的配额之内，也不需要在别人的云上开账号。"
    link: /docs/guides/use-cases/kubernetes-distribution/
    link_text: 作为 Kubernetes 发行版
  - title: 高校与科研
    situation: "每个课题组都想要自己的集群和一份 GPU 配额，却没有人愿意去运维其中任何一样。"
    outcome: "在共享硬件上为每个课题组或每门课程提供真正隔离的集群，在它们之间分配 GPU，并且下个学期可以从代码仓库重新拉起同样的环境。"
  - title: 公共部门与受监管行业
    situation: "数据不能离开你所在的司法辖区，外部控制面也不是你被允许去依赖的东西。"
    outcome: "整个平台运行在你自己的硬件上，控制路径中没有任何外部 SaaS，每一个组件都是可以审计的开源软件。"
  - title: 电信与边缘
    situation: "网络功能仍以虚拟机的形式交付，而所有新东西都以容器的形式到来，最后两者落在了互相分离的技术栈上。"
    outcome: "两者同处一个平台，并具备数据面所需的网络能力——从中心站点一直延伸到小型边缘集群。"

benefits:
  - title: API-first
    icon: fas fa-code
    description: >
      Cozystack 基于 Kubernetes，强调与其 API 的紧密交互。它并不追求把所有元素都隐藏在华丽的 UI 或各种定制背后，而是提供标准接口，并引导用户使用基本原语进行操作。
  - title: 标准化与统一
    icon: fas fa-certificate
    description: >
      平台的所有组件都构建在业界广泛认可的成熟开源工具和技术之上。
      我们力求采用最成熟、最经过验证的方案，让整个平台保持简单，并避免厂商锁定。
  - title: 协作而非竞争
    icon: fas fa-handshake
    description: >
      我们为自己的社区感到自豪，并与周边项目紧密协作。
      如果我们开发的某项平台功能对上游项目有用，
      我们更愿意将其贡献给该项目，而不是留在平台内部。
features:
  - title: 易于安装
    icon: fas fa-wrench
    description: >
      借助 [talos-bootstrap](https://github.com/cozystack/talos-bootstrap/)，我们提供了极其简单的安装方式，
      让你能够在裸数据中心的服务器上通过 PXE 或 ISO 方式引导 Cozystack。
      使用不可变操作系统有助于保持系统一致性，并确保一切按预期运行。
  - title: 易于集成
    icon: fas fa-plug
    description: >
      我们提供原生的 Kubernetes RESTful API，它以声明式而广为人知。
      因此，要与你的计费系统集成，只需让你的系统向 Kubernetes API 提交一份描述目标服务的特定 YAML 清单即可。
      其余的工作交给 Cozystack 完成。
  - title: 易于扩展
    icon: fas fa-up-right-and-down-left-from-center
    description: >
      平台中的每个软件包都由一组 YAML 文件构成。因此，任何熟悉 Kubernetes 原语的人都可以修改或扩展平台。软件包的交付由广为人知、应用广泛的 FluxCD 可靠完成。
  - title: 高性能、低开销
    icon: fas fa-gauge-high
    description: >
      我们重视性能。因此我们在稳定性与功能之间权衡，采用性能最佳的技术。
      此外，我们独特的租户模型能够为控制平面高效分配云资源，在保证必要安全级别的同时兼顾成本效益。
  - title: 内置监控与告警
    icon: fas fa-area-chart
    description: >
      每个服务的每个实例都配有一套预先配置的仪表盘和告警。
      你可以为每个租户创建独立的监控中心，也可以将它们合并为一个。
  - title: 内置应用管理 UI
    icon: fas fa-window-maximize
    description: >
      虽然平台的首要目标是提供优雅的 API，但它也提供了用于部署应用的仪表盘。
      该 Web UI 便于快速上手平台，并直观展示其能力。
---

<div class="hero-gitops">
  {{% blocks/hero title="Cozystack：基于 Kubernetes 的免费云平台" color="primary"
  height="auto" link_title="开始使用" link_url="/zh-cn/docs/v1.4/getting-started/" %}}
  将一组裸金属服务器变成智能系统，通过简单的 REST API 轻松创建 Kubernetes 集群、数据库即服务、虚拟机、负载均衡器、HTTP 缓存服务以及其他服务。

  使用 Cozystack 构建你自己的云，或提供高性价比的开发环境。

  {{% /blocks/hero %}}

  <div class="lead-flux">
  {{< blocks/lead >}}
  {{< /blocks/lead >}}
  </div>
</div>

<!-- Screenshot Gallery -->
{{< home/screenshot-gallery >}}

<!-- Live Demo -->
<div class="section-live-demo">
{{< blocks/lead color="primary" >}}
<h2 class="section-label">先看看控制台，再决定是否安装</h2>

真实的 Cozystack 仪表盘，完全在你的浏览器中运行——无需集群、无需注册、无需配置。浏览应用市场，打开托管服务，随意点击体验控制台。这就是真正的 UI，只是换成了演示数据。

<a class="btn btn-lg btn-primary mt-4" href="/demo/">打开在线演示 &rarr;</a>
{{< /blocks/lead >}}
</div>

<!-- Benefits & Features -->

{{< home/use-cases >}}

{{< home/benefits >}}

{{< home/features >}}

<!-- Community -->
<div class="section-community">
  {{< blocks/lead color="dark" >}}
  <h2 class="section-label">
  社区
  </h2>

  <p>我们衷心感谢社区对 Cozystack 成长一以贯之的支持与贡献。<br/> 加入我们的社区，成为我们旅程的一部分。</p>

  {{< /blocks/lead >}}

  <div class="subsection-community-row">
  {{< blocks/section color="dark" type="community-row">}}

  {{< home/community icon="fab fa-github" title="GitHub Discussions" >}}
  <a target="_blank" rel="noopener noreferrer" href="https://github.com/cozystack/cozystack/discussions">加入 GitHub Discussions 的讨论</a>。与 Cozystack 相关的一切——从规范、功能规划到 Show &amp; Tell——都在这里发生。

  {{< /home/community >}}

  {{< home/community icon="fab fa-slack" title="Slack" >}}
  如果你想与 Cozystack 团队和社区实时交流，欢迎加入我们的 Slack。这是结识大家的好方式。

  获取 <a target="_blank" rel="noopener noreferrer" href="https://slack.kubernetes.io/">Slack 邀请</a>，或前往 <a target="_blank" rel="noopener noreferrer" href="https://kubernetes.slack.com/messages/cozystack"><code>#cozystack</code> 频道</a>。

  {{< /home/community >}}

  {{< home/community icon="fa fa-paper-plane" title="Telegram" >}}
  我们在 Telegram 上也有一个庞大的社区。加入 <a target="_blank" rel="noopener noreferrer" href="https://t.me/cozystack/">@cozystack</a> 群聊，与其他用户交流、提问，并及时了解最新动态与进展。
  {{< /home/community >}}

  {{< /blocks/section >}}
  </div>

</div>

{{< home/cncf >}}
