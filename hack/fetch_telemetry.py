#!/usr/bin/env python3
"""
Fetch Cozystack telemetry and produce a JSON payload for the OSS Health shell.

What it does:
1. Query https://telemetry.cozystack.io/api/overview?year=YYYY&month=MM
2. Filter apps to entries visible on the Cozystack dashboard.
3. Merge case-insensitive / Pax* / legacy-name aliases into one canonical entry
   per application, keeping the maximum instance count (zero-count entries
   left after the merge are dropped from the table). Rows are emitted in a
   fixed canonical order (FIXED_ORDER) so the published table stays stable for
   copy-paste; apps not in that list are appended at the end (by count).
4. Surface the Tenants summary card from the API `total_tenants` field (now
   populated per period), falling back to the point-in-time `Tenant` entry in
   the apps map only when `total_tenants` is zero/absent.
5. Emit the payload in the shape consumed by `oss-health-app.html` +
   `renderTelemetry`, including `summary_cards`, `apps`, `range`.

Used by the monthly telemetry workflow and by developers who need to refresh or
backfill the seed file locally.
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


# Fixed canonical row order for the published table. Keeping this stable (rather
# than re-sorting by count every run) means the rows always line up for copy-paste
# into external spreadsheets. Apps not listed here are appended at the end, sorted
# by count desc — move them into this list once they should have a stable slot.
FIXED_ORDER: list[str] = [
    "VMDisk", "VMInstance", "Etcd", "Ingress", "Monitoring", "Kubernetes",
    "SeaweedFS", "Bucket", "Postgres", "MariaDB", "Harbor", "ClickHouse",
    "Redis", "VirtualPrivateCloud", "MongoDB", "Kafka", "OpenBAO", "RabbitMQ",
    "Qdrant", "NATS", "FoundationDB", "VPN", "TCPBalancer", "HTTPCache",
    "OpenSearch", "NFS", "ClearML",
]


def normalize_key(raw: str) -> str:
    return raw.lower().replace("-", "").replace("_", "")


def clean_apps(apps: dict[str, int]) -> list[dict[str, object]]:
    """Filter, dedupe (max), drop zeros, order by FIXED_ORDER (extras appended)."""
    merged: dict[str, int] = {}
    for raw_name, count in apps.items():
        canonical = ALIASES.get(normalize_key(raw_name))
        if not canonical:
            continue
        if count > merged.get(canonical, 0):
            merged[canonical] = count
    non_zero = {name: n for name, n in merged.items() if n > 0}
    rank = {name: i for i, name in enumerate(FIXED_ORDER)}
    ordered = sorted(
        non_zero.items(),
        key=lambda item: (rank.get(item[0], len(FIXED_ORDER)), -item[1], item[0].lower()),
    )
    return [{"name": name, "value": str(count)} for name, count in ordered]


def transform_period(raw_period: dict, label_fallback: str) -> dict | None:
    if not raw_period:
        return None
    apps_raw = raw_period.get("apps", {}) or {}
    # Prefer the per-period `total_tenants` field (now populated by the API);
    # fall back to the point-in-time `Tenant` entry only if it's zero/absent.
    tenants = int(raw_period.get("total_tenants") or 0) or int(apps_raw.get("Tenant", 0))
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
