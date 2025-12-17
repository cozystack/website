---
title: "Talm v0.17: Built-in Age Encryption for Secrets Management"
slug: talm-v0-17-built-in-age-encryption-for-secrets
date: 2025-12-17
author: "Andrei Kvapil (Ænix)"
description: "Talm v0.17 introduces built-in age encryption for secure secrets management, making it easier to store sensitive configuration files in Git repositories while maintaining security best practices."
---

### Talm v0.17: Built-in Age Encryption for Secrets Management

The latest release of [Talm](https://github.com/cozystack/talm), the configuration manager for Talos Linux, introduces a powerful new feature: built-in encryption using the [age](https://age-encryption.org/) encryption tool. This enhancement allows you to securely store sensitive configuration files like `secrets.yaml`, `talosconfig`, and `kubeconfig` in Git repositories while following security best practices.

![](https://cdn-images-1.medium.com/max/800/0*encryption.png)

### Why Age Encryption?

Managing secrets in Git repositories has always been a challenge. While storing configuration files in version control is convenient for GitOps workflows, sensitive data like API keys, certificates, and cluster credentials should never be committed in plain text. Traditional solutions like `git-crypt` or external secret management systems add complexity and dependencies.

Talm v0.17 solves this problem by integrating age encryption directly into the workflow. Age is a modern, simple, and secure file encryption tool that uses state-of-the-art cryptography. It's designed to be:

- **Simple**: Easy to use with minimal configuration
- **Secure**: Uses modern encryption algorithms (X25519, ChaCha20Poly1305)
- **Fast**: Efficient encryption and decryption
- **Compatible**: Works seamlessly with existing Git workflows

### SOPS-like Format for Encrypted Values

Talm uses a SOPS-like format for encrypted values, making it familiar to users who have worked with [Mozilla SOPS](https://github.com/getsops/sops). In encrypted YAML files, only the **values** are encrypted, while **keys** remain readable. This makes it easy to understand the structure of your configuration files even when encrypted.

Here's an example of how encrypted values look:

```yaml
machine:
  token: ENC[AGE,data:Tr7o=]
  ca:
    crt: ENC[AGE,data:VGVzdA==]
```

The `ENC[AGE,data:...]` format clearly indicates which values are encrypted, while the YAML structure remains intact and human-readable.

### Getting Started with Encryption

#### Initial Setup

When you run `talm init` for the first time, Talm automatically generates an encryption key (`talm.key`) if it doesn't exist. This key is used for all encryption and decryption operations:

```bash
talm init -p cozystack
```

This command will:
1. Generate `secrets.yaml` with your cluster secrets
2. Create `talosconfig` for cluster access
3. Generate `talm.key` (if it doesn't exist) for encryption
4. Automatically encrypt `secrets.yaml` to `secrets.encrypted.yaml`
5. Encrypt `talosconfig` to `talosconfig.encrypted`
6. Update `.gitignore` to exclude plain text files

#### The Encryption Key Format

The `talm.key` file follows the standard `age keygen` format, making it compatible with other age-based tools:

```
# created: 2025-01-17T15:18:42+01:00
# public key: age1uqwfv7lq6a23wslgpjqkpj8mnp6dmycwd97wmz4n6grtr7g2853sl0yjdr
AGE-SECRET-KEY-103PEFSPAV83H6GXECWZJ9CXCXJ3YRY64Y5PE75XWY2S97VAR84AQQ678AU
```

This format includes metadata about when the key was created and the public key, which can be used for sharing encrypted files with team members (though this feature is planned for future releases).

### Encrypting and Decrypting Files

#### Encrypting Files

To encrypt your sensitive files, use the `--encrypt` (or `-e`) flag:

```bash
talm init -e
```

This command will:
- Encrypt `secrets.yaml` → `secrets.encrypted.yaml`
- Encrypt `talosconfig` → `talosconfig.encrypted`
- Encrypt `kubeconfig` → `kubeconfig.encrypted` (if it exists)

The command provides detailed output showing which files are being encrypted:

```
Encrypting secrets.yaml -> secrets.encrypted.yaml
Encrypting talosconfig -> talosconfig.encrypted
Encrypting kubeconfig -> kubeconfig.encrypted
Encrypted 3 file(s).
```

#### Decrypting Files

To decrypt encrypted files back to plain text, use the `--decrypt` (or `-d`) flag:

```bash
talm init -d
```

This will decrypt all encrypted files:
- `secrets.encrypted.yaml` → `secrets.yaml`
- `talosconfig.encrypted` → `talosconfig`
- `kubeconfig.encrypted` → `kubeconfig`

### Idempotent Encryption: Only Changed Values Are Updated

One of the most powerful features of Talm's encryption is its **idempotent behavior**. When you run `talm init -e` multiple times, the system intelligently compares plain text values with their encrypted counterparts and only re-encrypts values that have actually changed.

This means:
- **Unchanged values** keep their existing encrypted form
- **Changed values** are re-encrypted with the latest plain text
- **New keys** are automatically encrypted
- The encrypted file only changes when necessary

This idempotent behavior ensures that:
1. Git diffs are minimal and meaningful
2. You can safely run encryption commands multiple times
3. Only actual changes trigger updates in version control

### Automatic .gitignore Management

Talm automatically manages your `.gitignore` file to ensure sensitive files are never accidentally committed:

- `secrets.yaml` - Plain text secrets (never commit)
- `talosconfig` - Plain text Talos configuration (never commit)
- `kubeconfig` - Plain text Kubernetes configuration (never commit)
- `talm.key` - Your encryption key (never commit)

The encrypted versions (`*.encrypted.yaml`, `*.encrypted`) are **intended to be committed** to your repository, as they are safe to store in version control.

### Security Best Practices

#### Backup Your Encryption Key

After `talm init` creates a new `talm.key`, you'll see a security warning:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Security Information                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Sensitive files (secrets.yaml, talosconfig, talm.key) have been added to    │
│  .gitignore and will not be tracked by git.                                  │
│                                                                              │
│  Important: Please make a backup of your talm.key file.                      │
│                                                                              │
│  The talm.key file is required to decrypt secrets.encrypted.yaml. Without it, │
│  you won't be able to decrypt your encrypted secrets.                         │
│                                                                              │
│  Key location: talm.key                                                      │
│                                                                              │
│  Recommended: Store the backup in a secure location (password manager,        │
│  encrypted storage, or other secure backup solution).                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Always backup your `talm.key` file!** Without it, you cannot decrypt your secrets. Store it in a secure location such as:
- A password manager
- Encrypted storage (e.g., encrypted USB drive)
- A secure backup solution

#### File Permissions

Talm automatically sets secure file permissions:
- `secrets.yaml`, `talosconfig`, and `kubeconfig` are created with `chmod 600` (read/write for owner only)
- This ensures that only the file owner can read these sensitive files

### Workflow Example

Here's a typical workflow for managing secrets with Talm v0.17:

1. **Initialize a new project:**
   ```bash
   talm init -p cozystack
   ```
   This creates all necessary files and encrypts them automatically.

2. **Make changes to secrets:**
   ```bash
   # Edit kubeconfig
   vim kubeconfig
   ```

3. **Re-encrypt after changes:**
   ```bash
   talm init -e
   ```
   Only changed values will be re-encrypted.

4. **Commit encrypted files to Git:**
   ```bash
   git add secrets.encrypted.yaml talosconfig.encrypted kubeconfig.encrypted
   git commit -m "Update encrypted secrets"
   ```

5. **On a new machine, decrypt files:**
   ```bash
   # Copy talm.key to the new machine first!
   talm init -d
   ```

### Integration with Existing Workflows

Talm's encryption integrates seamlessly with existing GitOps workflows:

- **CI/CD pipelines** can decrypt files using `talm init -d` if they have access to `talm.key`
- **Team collaboration** is easier: encrypted files can be shared via Git, while the key is shared securely through other channels
- **Audit trails** are maintained: all changes to encrypted files are tracked in Git history

### What's Next?

The encryption feature in Talm v0.17 provides a solid foundation for secure secrets management. Future releases may include:

- Support for multiple recipients (team members can decrypt with their own keys)
- Integration with hardware security modules (HSM)
- Automatic key rotation capabilities
- Integration with external key management systems

### Conclusion

Talm v0.17's built-in age encryption makes it significantly easier to manage sensitive configuration files in Git repositories while maintaining security best practices. The idempotent encryption behavior, automatic `.gitignore` management, and SOPS-like format create a seamless experience for teams adopting GitOps workflows with Talos Linux.

Whether you're managing a single cluster or multiple environments, Talm's encryption features help you maintain security without sacrificing the convenience of version-controlled configuration management.

### Get Started

- **GitHub**: [github.com/cozystack/talm](https://github.com/cozystack/talm)
- **Documentation**: Check the [README](https://github.com/cozystack/talm#readme) for detailed usage examples
- **Community**: Join the [Telegram chat](https://t.me/cozystack) to discuss Talm and get help

### Acknowledgments

Talm is developed as part of the [Cozystack](https://cozystack.io/) project and is released under the Apache 2.0 license. We welcome contributions and feedback from the community!

