#!/usr/bin/env python3
"""
Fetch Cozystack telemetry and produce a JSON payload for the OSS Health shell.

What it does:
1. Query https://telemetry.cozystack.io/api/overview?year=YYYY&month=MM
2. Filter apps to entries visible on the Cozystack dashboard.
3. Merge case-insensitive / Pax* / legacy-name aliases into one canonical entry
   per application, keeping the maximum instance count (zero-count entries
   left after the merge are dropped from the table).
4. Pull `Tenant` out of the apps map and surface it as the top-level Tenants
   summary card (the raw `total_tenants` field from the API is always zero).
5. Emit the payload in the shape consumed by `oss-health-app.html` +
   `renderTelemetry`, including `summary_cards`, `apps`, `range`.

Used by both `.github/workflows/fetch-telemetry.yml` (daily cron) and the
developer who needs to refresh the seed file locally.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://telemetry.cozystack.io/api/overview"
OUTPUT_PATH = os.environ.get(
    "TELEMETRY_OUTPUT_PATH",
    "static/oss-health-data/telemetry.json",
)

# Canonical display name per normalized key. Anything not in this table is
# dropped (internal entities like `Info`, `Pax*` experimental variants that
# don't map to a dashboard app, duplicate lowercase CR kind names, etc.).
# Keys are lower-cased and stripped of hyphens so we can match PascalCase,
# lowercase, kebab-case and Pax-prefixed variants against the same canonical.
ALIASES: dict[str, str] = {
    # Managed applications (docs/v1.2/applications/_include/*)
    "clickhouse": "ClickHouse",
    "paxclickhouse": "ClickHouse",
    "foundationdb": "FoundationDB",
    "harbor": "Harbor",
    "kafka": "Kafka",
    "mariadb": "MariaDB",
    "mongodb": "MongoDB",
    "nats": "NATS",
    "openbao": "OpenBAO",
    "opensearch": "OpenSearch",
    "postgres": "Postgres",
    "postgresql": "Postgres",
    "paxpostgres": "Postgres",
    "qdrant": "Qdrant",
    "rabbitmq": "RabbitMQ",
    "redis": "Redis",
    "paxredis": "Redis",
    "clearml": "ClearML",
    # Services (docs/v1.2/operations/services/*)
    "etcd": "Etcd",
    "ingress": "Ingress",
    "monitoring": "Monitoring",
    "bucket": "Bucket",
    "seaweedfs": "SeaweedFS",
    "nfs": "NFS",
    # Networking (docs/v1.2/networking/_include/*)
    "httpcache": "HTTPCache",
    "tcpbalancer": "TCPBalancer",
    "virtualprivatecloud": "VirtualPrivateCloud",
    "vpc": "VirtualPrivateCloud",
    "vpn": "VPN",
    # Virtualization (docs/v1.2/virtualization/_include/*)
    "vminstance": "VMInstance",
    "paxvminstance": "VMInstance",
    "vmdisk": "VMDisk",
    # Managed Kubernetes
    "kubernetes": "Kubernetes",
}


def normalize_key(raw: str) -> str:
    return raw.lower().replace("-", "").replace("_", "")


def clean_apps(apps: dict[str, int]) -> list[dict[str, object]]:
    """Filter, dedupe (max), drop zeros, sort desc by count."""
    merged: dict[str, int] = {}
    for raw_name, count in apps.items():
        canonical = ALIASES.get(normalize_key(raw_name))
        if not canonical:
            continue
        if count > merged.get(canonical, 0):
            merged[canonical] = count
    non_zero = [(name, n) for name, n in merged.items() if n > 0]
    non_zero.sort(key=lambda item: (-item[1], item[0].lower()))
    return [{"name": name, "value": str(count)} for name, count in non_zero]


def transform_period(raw_period: dict, label_fallback: str) -> dict | None:
    if not raw_period:
        return None
    apps_raw = raw_period.get("apps", {}) or {}
    tenants = int(apps_raw.get("Tenant", 0))
    clusters = int(raw_period.get("clusters", 0))
    total_nodes = int(raw_period.get("total_nodes", 0))
    avg_nodes = raw_period.get("avg_nodes_per_cluster")
    summary = [
        {"label": "Clusters", "value": str(clusters)},
        {
            "label": "Total Nodes",
            "value": str(total_nodes),
            "hint": (
                f"avg {avg_nodes:.1f} per cluster"
                if clusters and isinstance(avg_nodes, (int, float))
                else ""
            ),
        },
        {
            "label": "Tenants",
            "value": str(tenants),
            "hint": (
                f"avg {tenants / clusters:.1f} per cluster"
                if clusters
                else ""
            ),
        },
    ]
    period = {
        "label": raw_period.get("label") or label_fallback,
        "summary_cards": summary,
        "apps": clean_apps(apps_raw),
    }
    start = raw_period.get("start")
    end = raw_period.get("end")
    if start and end:
        period["range"] = {"from": start, "to": end}
    return period


def fetch(year: int, month: int) -> dict:
    url = f"{API_URL}?year={year}&month={month:02d}"
    req = urllib.request.Request(url, headers={"User-Agent": "cozystack-website/telemetry-fetch"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"telemetry API returned HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def build_payload(raw: dict) -> dict:
    periods_raw = raw.get("periods", {}) or {}
    periods_out: dict[str, dict] = {}
    for key in ("month", "quarter", "year"):
        transformed = transform_period(periods_raw.get(key, {}) or {}, label_fallback=key.title())
        if transformed:
            periods_out[key] = transformed
    return {
        "updated_at": raw.get("generated_at"),
        "title": "Telemetry",
        "source": {"label": "Cozystack Telemetry Server"},
        "periods": periods_out,
    }


def main() -> int:
    today = dt.datetime.now(dt.timezone.utc)
    year = int(os.environ.get("TELEMETRY_YEAR", today.year))
    month = int(os.environ.get("TELEMETRY_MONTH", today.month))
    try:
        raw = fetch(year, month)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError) as err:
        print(f"fetch failed: {err}", file=sys.stderr)
        return 1
    payload = build_payload(raw)
    if not payload["periods"]:
        print("fetched payload has no usable periods; refusing to write empty file", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {OUTPUT_PATH} ({len(payload['periods'])} periods, {sum(len(p['apps']) for p in payload['periods'].values())} app rows total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
