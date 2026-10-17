---
title: "Encryption at Rest"
linkTitle: "Encryption at Rest"
description: "Where Cozystack stores sensitive data and how to encrypt it with a key held outside the cluster"
weight: 38
---

Cozystack keeps sensitive data in several places: Kubernetes Secrets and application values in the management cluster etcd, Secrets of tenant Kubernetes clusters in their own etcd, and user data of the platform identity provider in PostgreSQL. This section explains what is encrypted by default, where the keys live, and how to move the keys out of the cluster into a key management service (KMS).

## What Is Encrypted by Default

| Data | Stored in | Default protection | With KMS |
| --- | --- | --- | --- |
| Secrets of the management cluster | Management cluster etcd | Encrypted by Talos with `secretbox`; the key is in the machine configuration of every control-plane node | [KMS v2 with Vault Transit](/docs/next/operations/encryption/etcd-kms/) |
| Application values (`spec` of every Cozystack application, which may contain passwords) | Management cluster etcd, inside Flux `HelmRelease` objects | Not encrypted | [KMS v2 with Vault Transit](/docs/next/operations/encryption/etcd-kms/#choose-what-to-encrypt), once `helmreleases` is added to the encrypted resources |
| Secrets of tenant Kubernetes clusters | etcd of the tenant | Not encrypted | Not supported yet; a [local key](/docs/next/operations/encryption/etcd-kms/#tenant-kubernetes-clusters) can be used |
| Users of the platform Keycloak (usernames, emails, names, credentials) | PostgreSQL of Keycloak | Not encrypted | [keycloak-kms-proxy](/docs/next/operations/encryption/keycloak/) |

The Cozystack API (`apps.cozystack.io`, `core.cozystack.io`) has no storage of its own: applications are stored as Flux `HelmRelease` objects and tenant secrets as regular Secrets, all in the management cluster etcd. Encrypting that etcd covers them.

## Why Move the Key Out

With the default `secretbox` encryption, the key sits on the same disks as the data it protects. A copy of a control-plane disk, or an etcd backup together with the machine configuration, is enough to read every Secret.

With KMS v2, kube-apiserver encrypts each object with a data encryption key, and that key is in turn encrypted by a key encryption key that never leaves the KMS. Decrypting data requires a call to the KMS from the control-plane nodes, so stolen disks and backups are useless on their own.

The guides in this section use [HashiCorp Vault](https://developer.hashicorp.com/vault/docs/secrets/transit) Transit as the KMS.
