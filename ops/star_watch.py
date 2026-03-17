from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

OWNER = os.getenv("REPO_OWNER", "luanyajun666-cell")
REPO = os.getenv("REPO_NAME", "spreadsynth")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Snapshot:
    timestamp: str
    stars_total: int
    watchers_total: int
    stars_last_1h: int
    stars_last_24h: int
    slope_stars_per_hour: float
    audience_breakdown_24h: dict[str, int]
    recent_users_24h: list[str]


def gh_get(url: str, *, accept: str = "application/vnd.github+json", params: dict[str, Any] | None = None):
    if not TOKEN:
        raise RuntimeError("GH_TOKEN/GITHUB_TOKEN is required")
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def classify_profile(user: dict[str, Any]) -> str:
    txt = " ".join(
        [
            str(user.get("bio") or ""),
            str(user.get("company") or ""),
            str(user.get("location") or ""),
            str(user.get("blog") or ""),
        ]
    ).lower()

    trader_kw = ["trader", "quant", "futures", "crypto", "portfolio", "finance", "commodity"]
    geek_kw = ["engineer", "developer", "ai", "open source", "backend", "frontend", "ml", "devops"]

    if any(k in txt for k in trader_kw):
        return "trader"
    if any(k in txt for k in geek_kw):
        return "geek"
    return "unknown"


def fetch_recent_stars(owner: str, repo: str):
    # starred_at requires custom media type
    events = gh_get(
        f"https://api.github.com/repos/{owner}/{repo}/stargazers",
        accept="application/vnd.github.star+json",
        params={"per_page": 100},
    )
    return events


def main() -> int:
    now = datetime.now(tz=timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(hours=24)

    repo_info = gh_get(f"https://api.github.com/repos/{OWNER}/{REPO}")
    stars_total = int(repo_info.get("stargazers_count", 0))
    watchers_total = int(repo_info.get("subscribers_count", 0))

    star_events = fetch_recent_stars(OWNER, REPO)
    stars_last_1h = 0
    stars_last_24h = 0
    recent_logins_24h: list[str] = []

    for e in star_events:
        ts = datetime.fromisoformat(e["starred_at"].replace("Z", "+00:00"))
        if ts >= one_hour_ago:
            stars_last_1h += 1
        if ts >= one_day_ago:
            stars_last_24h += 1
            recent_logins_24h.append(e["user"]["login"])

    # Background inference (heuristic only)
    counter = Counter()
    for login in recent_logins_24h[:20]:
        try:
            user = gh_get(f"https://api.github.com/users/{login}")
            counter[classify_profile(user)] += 1
        except Exception:
            counter["unknown"] += 1

    slope = round(float(stars_last_1h), 2)  # per hour snapshot

    snap = Snapshot(
        timestamp=now.isoformat(),
        stars_total=stars_total,
        watchers_total=watchers_total,
        stars_last_1h=stars_last_1h,
        stars_last_24h=stars_last_24h,
        slope_stars_per_hour=slope,
        audience_breakdown_24h=dict(counter),
        recent_users_24h=recent_logins_24h,
    )

    (OUT_DIR / "star_watch_snapshot.json").write_text(json.dumps(asdict(snap), ensure_ascii=False, indent=2), encoding="utf-8")

    report = []
    report.append(f"# Star Watch Snapshot ({now.strftime('%Y-%m-%d %H:%M UTC')})")
    report.append("")
    report.append(f"- Repo: https://github.com/{OWNER}/{REPO}")
    report.append(f"- Total Stars: **{stars_total}**")
    report.append(f"- Total Watchers: **{watchers_total}**")
    report.append(f"- Stars in last 1h: **{stars_last_1h}**")
    report.append(f"- Stars in last 24h: **{stars_last_24h}**")
    report.append(f"- Star slope (stars/hour): **{slope}**")
    report.append("")
    report.append("## Audience heuristic (last 24h stargazers)")
    if counter:
        for k, v in counter.items():
            report.append(f"- {k}: {v}")
    else:
        report.append("- no recent stargazers yet")

    report.append("")
    report.append("> Note: source channel (X/Reddit/etc.) is inferred heuristically from profile bio and cannot be guaranteed by GitHub API.")

    (OUT_DIR / "star_watch_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
