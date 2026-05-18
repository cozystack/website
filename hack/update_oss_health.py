#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import time
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from html import unescape
from pathlib import Path


REPO_OWNER = "cozystack"
REPO_NAME = "cozystack"
REPO_FULL_NAME = f"{REPO_OWNER}/{REPO_NAME}"
DATA_DIR = Path("data/oss-health")
STATIC_DATA_DIR = Path("static/oss-health-data")

GITHUB_API = "https://api.github.com"
OPENSSF_PROJECT_URL = "https://www.bestpractices.dev/projects/10177"
OPENSSF_BADGE_URL = "https://www.bestpractices.dev/projects/10177/badge"
OPENSSF_STATUS_URL = "https://www.bestpractices.dev/en/projects/10177/passing"
DEVSTATS_URL = "https://cozystack.devstats.cncf.io/"
OSSINSIGHT_URL = "https://ossinsight.io/analyze/cozystack/cozystack"

PERIODS = {
    "month": {"label": "Month", "days": 30, "description": "Last 30 days"},
    "quarter": {"label": "Quarter", "days": 90, "description": "Last 90 days"},
    "year": {"label": "Year", "days": 365, "description": "Last 365 days"},
}


def isoformat(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_link_header(value: str | None) -> dict[str, str]:
    links: dict[str, str] = {}
    if not value:
        return links
    for part in value.split(","):
        section = part.strip().split(";")
        if len(section) < 2:
            continue
        url = section[0].strip()[1:-1]
        rel = section[1].strip()
        if rel.startswith('rel="') and rel.endswith('"'):
            links[rel[5:-1]] = url
    return links


def build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "cozystack-website-oss-health-updater",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_json(url: str, headers: dict[str, str]) -> tuple[object, dict[str, str]]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
        return payload, dict(response.headers.items())


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "cozystack-website-oss-health-updater"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def paginate_json(url: str, headers: dict[str, str]) -> list[dict]:
    items: list[dict] = []
    next_url: str | None = url
    while next_url:
        payload, response_headers = fetch_json(next_url, headers)
        if not isinstance(payload, list):
            raise RuntimeError(f"Expected list payload for {next_url}")
        items.extend(payload)
        next_url = parse_link_header(response_headers.get("Link")).get("next")
    return items


def github_repo(headers: dict[str, str]) -> dict:
    payload, _ = fetch_json(f"{GITHUB_API}/repos/{REPO_FULL_NAME}", headers)
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected repository payload")
    return payload


def github_languages(headers: dict[str, str]) -> dict[str, int]:
    payload, _ = fetch_json(f"{GITHUB_API}/repos/{REPO_FULL_NAME}/languages", headers)
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected languages payload")
    return {str(key): int(value) for key, value in payload.items()}


def github_commits(since: datetime, until: datetime, headers: dict[str, str]) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "since": isoformat(since),
            "until": isoformat(until),
            "per_page": 100,
        }
    )
    return paginate_json(f"{GITHUB_API}/repos/{REPO_FULL_NAME}/commits?{params}", headers)


def github_contributor_stats(headers: dict[str, str]) -> list[dict]:
    request = urllib.request.Request(
        f"{GITHUB_API}/repos/{REPO_FULL_NAME}/stats/contributors",
        headers=headers,
    )
    attempts = 0
    while attempts < 6:
        attempts += 1
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status == 202:
                time.sleep(2)
                continue
            payload = json.load(response)
            if not isinstance(payload, list):
                raise RuntimeError("Unexpected contributor stats payload")
            return payload
    raise RuntimeError("GitHub contributor stats endpoint did not become ready in time")


def github_pulls_created(since: datetime, until: datetime, headers: dict[str, str]) -> list[dict]:
    page = 1
    pulls: list[dict] = []
    while True:
        params = urllib.parse.urlencode(
            {
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            }
        )
        payload, _ = fetch_json(f"{GITHUB_API}/repos/{REPO_FULL_NAME}/pulls?{params}", headers)
        if not isinstance(payload, list) or not payload:
            break
        stop = False
        for pull in payload:
            created_at = parse_datetime(pull["created_at"])
            if created_at < since:
                stop = True
                continue
            if created_at <= until:
                pulls.append(pull)
        if stop:
            break
        page += 1
    return pulls


def github_search_total(query: str, headers: dict[str, str]) -> int:
    params = urllib.parse.urlencode({"q": query, "per_page": 1})
    payload, _ = fetch_json(f"{GITHUB_API}/search/issues?{params}", headers)
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected search payload")
    return int(payload.get("total_count", 0))


def parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def compact_number(value: int) -> str:
    return f"{value:,}"


def contributor_name(commit: dict) -> tuple[str, str | None]:
    author = commit.get("author")
    if isinstance(author, dict) and author.get("login"):
        return author["login"], author.get("html_url")
    commit_author = commit.get("commit", {}).get("author", {})
    return commit_author.get("name", "Unknown"), None


def pull_author(pull: dict) -> tuple[str, str | None]:
    user = pull.get("user") or {}
    return user.get("login", "Unknown"), user.get("html_url")


def build_period_report(
    report_kind: str,
    since: datetime,
    until: datetime,
    repo: dict,
    languages: dict[str, int],
    headers: dict[str, str],
    contributor_stats: list[dict] | None,
    all_pulls: list[dict],
    all_commits: list[dict] | None = None,
) -> dict:
    pulls = [pull for pull in all_pulls if since <= parse_datetime(pull["created_at"]) <= until]

    commit_counter: Counter[str] = Counter()
    commit_links: dict[str, str | None] = {}
    if contributor_stats:
        for contributor in contributor_stats:
            user = contributor.get("author") or {}
            name = user.get("login", "Unknown")
            url = user.get("html_url")
            commits_in_period = 0
            for week in contributor.get("weeks", []):
                week_start = datetime.fromtimestamp(int(week["w"]), tz=UTC)
                week_end = week_start + timedelta(days=7)
                if week_end > since and week_start <= until:
                    commits_in_period += int(week.get("c", 0))
            if commits_in_period:
                commit_counter[name] = commits_in_period
                commit_links[name] = url
    elif all_commits:
        for commit in all_commits:
            committed_at = parse_datetime(commit["commit"]["author"]["date"])
            if not (since <= committed_at <= until):
                continue
            name, url = contributor_name(commit)
            commit_counter[name] += 1
            commit_links.setdefault(name, url)

    pr_author_counter: Counter[str] = Counter()
    pr_author_links: dict[str, str | None] = {}
    merged_prs = 0
    for pull in pulls:
        name, url = pull_author(pull)
        pr_author_counter[name] += 1
        pr_author_links.setdefault(name, url)
        merged_at = pull.get("merged_at")
        if merged_at:
            merged_time = parse_datetime(merged_at)
            if since <= merged_time <= until:
                merged_prs += 1

    date_range = f"{since.date().isoformat()}..{until.date().isoformat()}"
    prs_opened = len(pulls)
    issues_opened = github_search_total(f"repo:{REPO_FULL_NAME} is:issue created:{date_range}", headers)
    issues_closed = github_search_total(f"repo:{REPO_FULL_NAME} is:issue closed:{date_range}", headers)

    top_languages = [
        {"name": name, "value": compact_number(bytes_of_code)}
        for name, bytes_of_code in sorted(languages.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    summary_cards = [
        {"label": "Commits", "value": compact_number(sum(commit_counter.values()))},
        {"label": "Contributors", "value": compact_number(len(commit_counter))},
        {"label": "PR Authors", "value": compact_number(len(pr_author_counter))},
        {"label": "PRs Opened", "value": compact_number(prs_opened)},
        {"label": "PRs Merged", "value": compact_number(merged_prs)},
        {"label": "Issues Closed", "value": compact_number(issues_closed)},
    ]

    if report_kind == "ossinsight":
        summary_cards = [
            {"label": "Stars", "value": compact_number(int(repo.get("stargazers_count", 0)))},
            {"label": "Forks", "value": compact_number(int(repo.get("forks_count", 0)))},
            {"label": "Watchers", "value": compact_number(int(repo.get("subscribers_count", 0)))},
            {"label": "Open Issues", "value": compact_number(int(repo.get("open_issues_count", 0)))},
            {"label": "Commits", "value": compact_number(sum(commit_counter.values()))},
            {"label": "PRs Merged", "value": compact_number(merged_prs)},
        ]

    return {
        "label": "",
        "description": "",
        "range": {
            "from": since.date().isoformat(),
            "to": until.date().isoformat(),
        },
        "summary_cards": summary_cards,
        "top_contributors": [
            {"name": name, "value": compact_number(count), "url": commit_links.get(name)}
            for name, count in commit_counter.most_common(10)
        ],
        "top_pr_authors": [
            {"name": name, "value": compact_number(count), "url": pr_author_links.get(name)}
            for name, count in pr_author_counter.most_common(10)
        ],
        "languages": top_languages,
        "issues_opened": compact_number(issues_opened),
        "issues_closed": compact_number(issues_closed),
    }


def build_devstats(
    repo: dict,
    languages: dict[str, int],
    headers: dict[str, str],
    now: datetime,
    contributor_stats: list[dict] | None,
    all_pulls: list[dict],
    all_commits: list[dict] | None = None,
) -> dict:
    periods: dict[str, dict] = {}
    for period_key, config in PERIODS.items():
        since = now - timedelta(days=config["days"])
        period_report = build_period_report("devstats", since, now, repo, languages, headers, contributor_stats, all_pulls, all_commits)
        period_report["label"] = config["label"]
        period_report["description"] = config["description"]
        periods[period_key] = period_report

    return {
        "title": "DevStats",
        "source": {"label": "CNCF DevStats", "url": DEVSTATS_URL},
        "updated_at": isoformat(now),
        "periods": periods,
    }


def build_ossinsight(
    repo: dict,
    languages: dict[str, int],
    headers: dict[str, str],
    now: datetime,
    contributor_stats: list[dict] | None,
    all_pulls: list[dict],
    all_commits: list[dict] | None = None,
) -> dict:
    periods: dict[str, dict] = {}
    for period_key, config in PERIODS.items():
        since = now - timedelta(days=config["days"])
        period_report = build_period_report("ossinsight", since, now, repo, languages, headers, contributor_stats, all_pulls, all_commits)
        period_report["label"] = config["label"]
        period_report["description"] = config["description"]
        periods[period_key] = period_report

    return {
        "title": "OSS Insight",
        "source": {"label": "OSS Insight", "url": OSSINSIGHT_URL},
        "updated_at": isoformat(now),
        "periods": periods,
    }


def parse_openssf_state(page_text: str) -> str:
    lowered = page_text.lower()
    if "passing" in lowered:
        return "Passing"
    if "in progress" in lowered:
        return "In Progress"
    return "Unknown"


def parse_openssf_last_updated(page_text: str) -> str | None:
    plain_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page_text))
    match = re.search(r"last updated on\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC)", plain_text, re.IGNORECASE)
    if not match:
        return None
    try:
        dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC)
    except ValueError:
        return None
    return isoformat(dt)


def parse_openssf_project_name(page_text: str) -> str | None:
    match = re.search(r"<title>\s*([^<]+?)\s*\|\s*BadgeApp", page_text, re.IGNORECASE)
    if not match:
        return None
    return unescape(match.group(1).strip())


def build_openssf(now: datetime) -> dict:
    page_text = fetch_text(OPENSSF_STATUS_URL)
    return {
        "title": "OpenSSF",
        "source": {"label": "OpenSSF Best Practices", "url": OPENSSF_PROJECT_URL},
        "updated_at": isoformat(now),
        "project_name": parse_openssf_project_name(page_text) or "Cozystack",
        "state": parse_openssf_state(page_text),
        "badge_url": OPENSSF_BADGE_URL,
        "project_url": OPENSSF_PROJECT_URL,
        "status_url": OPENSSF_STATUS_URL,
        "last_checked_at": isoformat(now),
        "badge_last_updated_at": parse_openssf_last_updated(page_text),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_outputs(devstats: dict, ossinsight: dict, openssf: dict) -> None:
    summary = {
        "updated_at": isoformat(datetime.now(UTC)),
        "reports": [
            {"key": "devstats", "title": devstats["title"], "url": "/oss-health/devstats/"},
            {"key": "openssf", "title": openssf["title"], "url": "/oss-health/openssf/"},
            {"key": "ossinsight", "title": ossinsight["title"], "url": "/oss-health/oss-insight/"},
        ],
    }

    for directory in (DATA_DIR, STATIC_DATA_DIR):
        write_json(directory / "devstats.json", devstats)
        write_json(directory / "ossinsight.json", ossinsight)
        write_json(directory / "openssf.json", openssf)
        write_json(directory / "summary.json", summary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()

    if args.render_only:
        devstats = load_json(DATA_DIR / "devstats.json")
        ossinsight = load_json(DATA_DIR / "ossinsight.json")
        openssf = load_json(DATA_DIR / "openssf.json")
        render_outputs(devstats, ossinsight, openssf)
        print("OSS health assets rendered from local data.", file=sys.stderr)
        return 0

    now = datetime.now(UTC)
    headers = build_headers()

    try:
        print("Fetching repository metadata...", file=sys.stderr)
        repo = github_repo(headers)
        languages = github_languages(headers)
        year_since = now - timedelta(days=PERIODS["year"]["days"])
        print("Fetching contributor stats...", file=sys.stderr)
        contributor_stats = None
        all_commits = None
        try:
            contributor_stats = github_contributor_stats(headers)
        except RuntimeError:
            print("Contributor stats were not ready; falling back to raw commits.", file=sys.stderr)
            print("Fetching commits for the last year...", file=sys.stderr)
            all_commits = github_commits(year_since, now, headers)
        print("Fetching pull requests for the last year...", file=sys.stderr)
        all_pulls = github_pulls_created(year_since, now, headers)
        print("Building DevStats snapshot...", file=sys.stderr)
        devstats = build_devstats(repo, languages, headers, now, contributor_stats, all_pulls, all_commits)
        print("Building OSS Insight snapshot...", file=sys.stderr)
        ossinsight = build_ossinsight(repo, languages, headers, now, contributor_stats, all_pulls, all_commits)
        print("Fetching OpenSSF state...", file=sys.stderr)
        openssf = build_openssf(now)
    except urllib.error.HTTPError as exc:
        print(f"HTTP error while updating OSS health data: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error while updating OSS health data: {exc.reason}", file=sys.stderr)
        return 1

    render_outputs(devstats, ossinsight, openssf)
    print("OSS health data updated.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
