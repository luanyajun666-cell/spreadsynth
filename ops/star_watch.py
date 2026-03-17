from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
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
    potential_big_shots: list[str]


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


def classify_domain(user: dict[str, Any]) -> str:
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


def classify_tier(user: dict[str, Any]) -> str:
    followers = int(user.get("followers") or 0)
    public_repos = int(user.get("public_repos") or 0)
    txt = " ".join(
        [
            str(user.get("bio") or ""),
            str(user.get("company") or ""),
        ]
    ).lower()

    signal_kw = ["founder", "staff", "investor", "cto", "principal", "maintainer"]
    if followers >= 500 or public_repos >= 100 or any(k in txt for k in signal_kw):
        return "potential_big_shot"
    return "regular_developer"


def fetch_recent_stars(owner: str, repo: str):
    return gh_get(
        f"https://api.github.com/repos/{owner}/{repo}/stargazers",
        accept="application/vnd.github.star+json",
        params={"per_page": 100},
    )


def draft_thank_you(login: str, tier: str, domain: str) -> str:
    if tier == "potential_big_shot":
        return (
            f"Hi @{login}, appreciate the star — your profile looks deeply experienced in {domain}. "
            f"If you're open, I’d love your take on our scoring weights (D/T/C/A/K/F) and real-time iron-ore API design for v0.1.1."
        )
    return (
        f"Thanks @{login} for starring SpreadSynth! If you have a use case, open an issue and I’ll help map it into a runnable strategy template."
    )


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

    counter = Counter()
    user_rows: list[dict[str, Any]] = []
    potential_big_shots: list[str] = []

    for login in recent_logins_24h[:20]:
        try:
            user = gh_get(f"https://api.github.com/users/{login}")
            domain = classify_domain(user)
            tier = classify_tier(user)
            counter[domain] += 1
            if tier == "potential_big_shot":
                potential_big_shots.append(login)
            user_rows.append(
                {
                    "login": login,
                    "domain": domain,
                    "tier": tier,
                    "followers": int(user.get("followers") or 0),
                    "public_repos": int(user.get("public_repos") or 0),
                    "thank_you_draft": draft_thank_you(login, tier, domain),
                }
            )
        except Exception:
            counter["unknown"] += 1

    slope = round(float(stars_last_1h), 2)

    snap = Snapshot(
        timestamp=now.isoformat(),
        stars_total=stars_total,
        watchers_total=watchers_total,
        stars_last_1h=stars_last_1h,
        stars_last_24h=stars_last_24h,
        slope_stars_per_hour=slope,
        audience_breakdown_24h=dict(counter),
        recent_users_24h=recent_logins_24h,
        potential_big_shots=potential_big_shots,
    )

    (OUT_DIR / "star_watch_snapshot.json").write_text(json.dumps(asdict(snap), ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "star_watch_users.json").write_text(json.dumps(user_rows, ensure_ascii=False, indent=2), encoding="utf-8")

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
    report.append("## Potential big shots")
    if potential_big_shots:
        for u in potential_big_shots:
            report.append(f"- @{u}")
    else:
        report.append("- none yet")

    if user_rows:
        report.append("")
        report.append("## Thank-you drafts")
        for u in user_rows[:5]:
            report.append(f"- @{u['login']} ({u['tier']}, {u['domain']}): {u['thank_you_draft']}")

    report.append("")
    report.append("> Note: source channel (X/Reddit/etc.) cannot be directly obtained via GitHub API; attribution is heuristic only.")

    (OUT_DIR / "star_watch_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
