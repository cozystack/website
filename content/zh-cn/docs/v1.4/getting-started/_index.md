---
title: "Cozystack 入门：从零部署私有云"
linkTitle: "入门"
description: "迈出第一步，搭建家庭实验室，用 Cozystack 构建 PoC。"
weight: 10
aliases:
  - /docs/v1.4/get-started
source_digest: "sha256:0e11921728e455b5e48db02f13a3dacf4a0024b7f556cbe05bfb342384b90a4f"
translation_status: current
l10n: mt
---

本教程将引导你完成首次部署 Cozystack 集群。
在此过程中，你将了解关键概念，学会通过仪表盘和 CLI 使用 Cozystack，
并获得一个可运行的概念验证（PoC）。

本教程分为多个步骤。
请确保完成每一步后再开始下一步：

| 步骤                                                                              | 说明                                                                                                                           |
|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| [前置条件：准备基础设施和工具](/docs/v1.4/getting-started/requirements/)                          | 在运行本教程之前，请准备基础设施并在本机安装所需的 CLI 工具。                                                                  |
| 1. [安装 Talos Linux](/docs/v1.4/getting-started/install-talos/)                                | 使用 [`boot-to-talos`][btt] 安装 Cozystack 专用的 Talos Linux 发行版，这可能是最简单的安装方法。                                |
| 2. [安装并引导 Kubernetes 集群](/docs/v1.4/getting-started/install-kubernetes/)                  | 使用 [Talm][talm]（专为 Cozystack 打造的 Talos 配置管理工具）引导 Kubernetes 集群。                                             |
| 3. [安装并配置 Cozystack](/docs/v1.4/getting-started/install-cozystack/)                        | 安装 Cozystack，获取管理员访问权限，完成基本配置，并访问 Cozystack 仪表盘。                                                     |
| 4. [为用户和团队创建租户](/docs/v1.4/getting-started/create-tenant/)                             | 创建用户租户（Cozystack 中 RBAC 的基础），并通过仪表盘和 Cozystack API 访问该租户。                                            |
| 5. [部署托管应用](/docs/v1.4/getting-started/deploy-app/)                                       | 开始使用 Cozystack：部署虚拟机、托管应用和租户的 Kubernetes 集群。                                                             |

[btt]: https://github.com/cozystack/boot-to-talos
[talm]: https://github.com/cozystack/talm
