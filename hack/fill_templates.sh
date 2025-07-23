#!/bin/bash

GITHUB_REPO="cozystack/cozystack"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main/packages/apps"

apps=(
  tenant clickhouse virtual-machine redis vpn ferretdb vm-disk
  rabbitmq postgres nats kafka mysql vm-instance
  kubernetes http-cache tcp-balancer
)

for app in "${apps[@]}"; do
  readme_url="${RAW_BASE_URL}/${app}/README.md"

  echo "Processing $app..."

  # Fetch the first line of the README
  first_line=$(curl -fsSL "$readme_url" | head -n 1)

  if [[ $? -ne 0 || -z "$first_line" ]]; then
    echo "⚠️ Failed to fetch README or no title for $app"
    continue
  fi

  # Remove leading '# ' and trim whitespace
  title=$(echo "$first_line" | sed 's/^#*\s*//' | xargs)
  link_title=$(echo "$title" | sed -E 's/\b(Managed|Service)\b//Ig' | xargs)

  # Write to the markdown file
  cat > "${app}.md" <<EOF
---
title: "$title"
linkTitle: "$link_title"
---

EOF

  echo "✓ Wrote metadata for $app"
done