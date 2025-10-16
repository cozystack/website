---
title: "Introducing Talm, a configuration manager for Talos Linux"
slug: introducing-talm-a-configuration-manager-for-talos-linux
date: 2024-05-29
---

**Author**: Andrei Kvapil (Ænix)

The Cozystack project has released Talm, a configuration manager for Talos Linux

The developers of the open-source PaaS platform [Cozystack](https://cozystack.io/) have prepared the [Talm](https://github.com/cozystack/talm) project, aimed at simplifying the configuration of bare-metal servers for [Talos Linux](https://www.talos.dev/), an operating system designed to run Kubernetes with a Kubernetes-like API and configured via a single Yaml manifest. Although Talm was created to describe the declarative installation of Cozystack, it is not tied specifically to this platform and can be used to manage any Talos Linux configurations. The project is developed under the MPL license.

The need to develop another configuration manager for Talos Linux stems from its focus on bare-metal servers. The developers aimed to create the simplest interface possible, similar to well-known Kubernetes administration tools like Helm and kubectl.

Given that each physical server has different configurations (MAC addresses, interfaces, and disks), it is necessary to have a separate configuration file for each node. A simple manager is needed that can generate such configuration files based on collected information and declaratively update them.

This is achieved through dynamic generation of configuration files from a given template. There are ready presets `generic` and `cozystack`. During the generation phase, Talm can collect information from the Talos API and use it for the resulting configurations. These configuration files contain no secrets, only changes, which makes it convenient to store and manage them declaratively in Git.

In many aspects, Talm replicates the structure of Helm, using the concept of a chart in which templates for generating configurations are described. It supports Helm-like lookup functions for directly querying the Talos API and collecting additional metadata for generating configuration files using go templates and the [sprig](http://masterminds.github.io/sprig/) library.

Commands:

```bash
talm template -t templates/controlplane.yaml -e 1.2.3.4 -n 1.2.3.4 > nodes/srv1.yaml
```

This queries the node `1.2.3.4` via the API, generates a new configuration file from the template, inserting the necessary data. The resulting configuration file can be immediately applied with just one command:

```bash
talm apply -f nodes/srv1.yaml
```

Also, each configuration file set by Talm includes its own modeline, which remembers the node's endpoints and the templates from which it was obtained, making them convenient to apply and update without additional options. Talm supports all the same commands as the upstream utility talosctl, but allows passing the node's configuration file, for example:

```bash
talm dashboard -f nodes/srv1.yaml -f nodes/srv2.yaml -f nodes/srv3.yaml
```

displays an interactive dashboard for all three nodes. And the command:

```bash
talm get routes -f nodes/srv1.yaml
```

displays a list of routes on the node `srv1`

If necessary, configuration files can be exported with the `--full` option to a separate PXE server, allowing nodes to automatically download them. Thus, Talm maintains the versatility of bare-metal servers, providing convenient management in accordance with the best practices of GitOps.
