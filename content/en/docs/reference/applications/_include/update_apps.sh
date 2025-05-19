#!/bin/bash

GITHUB_REPO="cozystack/cozystack"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main/packages/apps"

apps=(
  tenant clickhouse virtual-machine redis vpn ferretdb vm-disk
  rabbitmq postgres nats bucket kafka mysql vm-instance
  kubernetes http-cache tcp-balancer
)

for app in "${apps[@]}"; do
  src_file="${app}.md"
  dest_file="../${src_file}"

  # Create empty file if it doesn't exist
  [ -f "$src_file" ] || touch "$src_file"

  # Copy to parent directory
  cp "$src_file" "$dest_file"

  # Construct raw GitHub URL
  readme_url="${RAW_BASE_URL}/${app}/README.md"

  echo "Processing $app..."

  # Download README content and append
  {
    curl -fsSL "$readme_url" | awk 'NR==1 && /^#{1,2} / { next } { print }'
  } >> "$dest_file"

  if [ $? -eq 0 ]; then
    echo "✓ Appended README for $app"
  else
    echo "⚠️ Failed to fetch README for $app"
  fi
done
