---
title: "White Labeling"
linkTitle: "White Labeling"
description: "Customize branding elements in the Cozystack Dashboard and Keycloak authentication pages, including custom Keycloak themes"
weight: 50
---

White labeling allows you to replace default Cozystack branding with your own logos and text across the Dashboard UI and Keycloak authentication pages.

## Overview

Branding is configured through the `branding` field in the Platform Package (`spec.components.platform.values.branding`). The configuration propagates automatically to:

- **Dashboard**: logo, page title, footer text, favicon, and tenant identifier
- **Keycloak**: realm display name on authentication pages

## Configuration

Edit your Platform Package to add or update the `branding` section:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full # use your variant
  components:
    platform:
      values:
        branding:
          # Dashboard branding
          titleText: "My Company Dashboard"
          footerText: "My Company Platform"
          tenantText: "Production v1.0"
          logoText: ""
          logoSvg: "<base64-encoded SVG>"
          iconSvg: "<base64-encoded SVG>"
          # Keycloak branding
          brandName: "My Company"
          brandHtmlName: "<div style='font-weight:bold;'>My Company</div>"
```

Apply the changes:

```bash
kubectl apply --server-side --filename platform-package.yaml
```

## Configuration Fields

### Dashboard Fields

| Field | Default | Description |
| --- | --- | --- |
| `titleText` | `Cozystack Dashboard` | Browser tab title and Dashboard header text. |
| `footerText` | `Cozystack` | Text displayed in the Dashboard footer. |
| `tenantText` | Platform version string | Version or tenant identifier displayed in the Dashboard. |
| `logoText` | `""` (empty) | Alternative text-based logo. Used when SVG logo is not provided. |
| `logoSvg` | Cozystack logo (base64) | Base64-encoded SVG logo displayed in the Dashboard header. |
| `iconSvg` | Cozystack icon (base64) | Base64-encoded SVG icon used as the browser favicon. |

### Keycloak Fields

| Field | Default | Description |
| --- | --- | --- |
| `brandName` | Not set | Plain text realm name displayed in the Keycloak browser tab. |
| `brandHtmlName` | Not set | HTML-formatted realm name displayed on Keycloak login pages. Supports inline HTML/CSS for styled branding. |

## Preparing SVG Logos

### Theme-Aware SVG Variables

The Dashboard supports template variables in SVG content that adapt to light and dark themes:

- `{token.colorText}` — replaced at runtime with the current theme's text color

{{< note >}}
The `{token.colorText}` syntax is **not valid XML**. The attribute value is intentionally unquoted because the Dashboard performs raw string substitution on the SVG source before rendering — it replaces `{token.colorText}` with the actual color value. This means SVG files with these placeholders cannot be opened directly in a browser or validated with an XML parser. This is expected and matches the upstream Dashboard implementation.
{{< /note >}}

Example SVG using a theme-aware variable:

```text
<svg width="150" height="30" viewBox="0 0 150 30" fill="none"
     xmlns="http://www.w3.org/2000/svg">
  <path d="M10 5h30v20H10z" fill={token.colorText} />
  <text x="50" y="20" fill={token.colorText}>My Company</text>
</svg>
```

### Converting SVG to Base64

Encode your SVG files to base64 strings:

```bash
base64 < logo.svg | tr -d '\n'
```

### Example Workflow

```bash
# Encode logos
LOGO_B64=$(base64 < logo.svg | tr -d '\n')
ICON_B64=$(base64 < icon.svg | tr -d '\n')

# Patch the Platform Package
kubectl patch packages.cozystack.io cozystack.cozystack-platform \
  --type merge --server-side \
  --patch "{
    \"spec\": {
      \"components\": {
        \"platform\": {
          \"values\": {
            \"branding\": {
              \"logoSvg\": \"$LOGO_B64\",
              \"iconSvg\": \"$ICON_B64\"
            }
          }
        }
      }
    }
  }"
```

## Verification

After applying changes, verify that branding is correctly configured:

1. **Check the Platform Package**:

   ```bash
   kubectl get packages.cozystack.io cozystack.cozystack-platform \
     --output jsonpath='{.spec.components.platform.values.branding}' | jq .
   ```

2. **Dashboard**: open the Dashboard URL and verify the logo, title, footer, and favicon.

3. **Keycloak**: open the Keycloak login page and verify the realm display name.

{{< note >}}
You may need to hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) or clear browser cache to see updated branding.
{{< /note >}}

## Custom Keycloak Themes

For deeper visual customization of Keycloak authentication pages (login, registration, account management), you can inject custom themes built as container images.

### Theme Image Contract

A theme image must contain theme files under the `/themes/` directory. The directory structure should follow the standard [Keycloak theme format](https://www.keycloak.org/docs/latest/server_development/index.html#_themes):

```text
/themes/
  my-brand/
    login/
      theme.properties
      resources/
        css/
        img/
    account/
      theme.properties
```

At pod startup, init containers copy files from each theme image into Keycloak's `/opt/keycloak/themes/` directory. Built-in Keycloak themes (bundled in JAR files) are not affected.

If multiple theme images contain files at the same path, later entries in the list take precedence.

### Configuration

Custom themes are configured on the Keycloak system component. Edit the `cozystack.keycloak` Package:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.keycloak
  namespace: cozy-system
spec:
  variant: default
  components:
    keycloak:
      values:
        themes:
          - name: my-brand
            image: registry.example.com/my-keycloak-theme:v1.0
```

Apply the changes:

```bash
kubectl apply --server-side --filename keycloak-package.yaml
```

### Theme Fields

| Field | Required | Description |
| --- | --- | --- |
| `name` | Yes | Theme identifier. Used as init container name (sanitized to DNS-1123 format). |
| `image` | Yes | Container image containing theme files under `/themes/`. |

### Private Registries

If your theme images are stored in a private registry, add `imagePullSecrets`:

```yaml
keycloak:
  values:
    themes:
      - name: my-brand
        image: private-registry.example.com/my-keycloak-theme:v1.0
    imagePullSecrets:
      - name: my-registry-secret
```

The referenced Secret must exist in the `cozy-keycloak` namespace.

### Activating a Custom Theme

After deploying a theme image, activate it in Keycloak:

1. Open the Keycloak admin console.
2. Navigate to **Realm Settings** > **Themes**.
3. Select your custom theme from the dropdown for the desired theme type (login, account, email, or admin).
4. Save the changes.

## Migration from v0

In Cozystack v0, branding was configured via a standalone `cozystack-branding` ConfigMap in the `cozy-system` namespace. In v1, this ConfigMap is no longer used. The [migration script]({{% ref "/docs/v1.3/operations/upgrades#step-3-generate-the-platform-package" %}}) automatically converts the old ConfigMap values into the Platform Package `branding` field.

If you previously used the ConfigMap approach, no manual migration is needed — the upgrade process handles it automatically.
