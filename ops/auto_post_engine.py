from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

BJT = ZoneInfo("Asia/Shanghai")
ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "ops" / ".post_state.json"
LOG_PATH = ROOT / "ops" / ".autopilot.log"

X_THREAD_PATH = ROOT / "docs" / "launch-pack" / "x-thread.md"
V2EX_POST_PATH = ROOT / "docs" / "launch-pack" / "v2ex-day1-official-with-iron-ore.md"
HN_POST_PATH = ROOT / "docs" / "launch-pack" / "hn-show-hn-en.md"

SCHEDULE = {
    "x_thread": "08:30",
    "v2ex_post": "09:05",
    "hn_post": "12:30",
    "booster_check": "10:00",
}


class CircuitBreak(Exception):
    pass


@dataclass
class EnvCfg:
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    x_bearer_token: str = ""
    v2ex_cookie: str = ""
    hn_cookie: str = ""
    gh_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    feishu_webhook: str = ""


def log(msg: str) -> None:
    line = f"[{datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S %Z')}] {msg}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def guard_and_unstage_env() -> None:
    """熔断保护：发现 .env 暂存，立刻取消并中止。"""
    code, out = run(["git", "diff", "--cached", "--name-only"])
    if code != 0:
        return
    staged = {line.strip() for line in out.splitlines() if line.strip()}
    if ".env" in staged or any(x.startswith(".env") for x in staged):
        run(["git", "restore", "--staged", ".env"])
        run(["git", "reset", "HEAD", ".env"])
        raise CircuitBreak("SECURITY FUSE: .env was staged. Staging cleared and autopilot stopped.")


def load_env(path: Path) -> EnvCfg:
    if not path.exists():
        return EnvCfg()
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return EnvCfg(
        x_api_key=data.get("X_API_KEY", ""),
        x_api_secret=data.get("X_API_SECRET", ""),
        x_access_token=data.get("X_ACCESS_TOKEN", ""),
        x_access_token_secret=data.get("X_ACCESS_TOKEN_SECRET", ""),
        x_bearer_token=data.get("X_BEARER_TOKEN", ""),
        v2ex_cookie=data.get("V2EX_COOKIE", ""),
        hn_cookie=data.get("HN_COOKIE", ""),
        gh_token=data.get("GH_TOKEN", ""),
        telegram_bot_token=data.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=data.get("TELEGRAM_CHAT_ID", ""),
        feishu_webhook=data.get("FEISHU_WEBHOOK", ""),
    )


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "date": datetime.now(BJT).strftime("%Y-%m-%d"),
        "done": {},
        "x_thread_ids": [],
        "last_monitor_ts": None,
        "booster_done": False,
    }


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_hhmm_today(hhmm: str) -> datetime:
    h, m = hhmm.split(":")
    now = datetime.now(BJT)
    return now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)


def due(hhmm: str) -> bool:
    return datetime.now(BJT) >= parse_hhmm_today(hhmm)


def parse_x_thread(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n## Tweet \d+.*\n", text)
    # first segment is title, remove
    segments = [p.strip() for p in parts[1:] if p.strip()]

    tweets: list[str] = []
    for seg in segments:
        # remove fenced code, keep readable text
        seg = re.sub(r"```[\s\S]*?```", "", seg).strip()
        seg = seg.replace("(Attach image: `assets/backtest-iron-ore-9724.png`)", "")
        seg = re.sub(r"\n{3,}", "\n\n", seg)
        tweets.append(seg)

    # ensure tweet 1 includes public image link
    if tweets:
        img_url = "https://raw.githubusercontent.com/luanyajun666-cell/spreadsynth/main/assets/backtest-iron-ore-9724.png"
        if img_url not in tweets[0]:
            tweets[0] += f"\n\nChart: {img_url}"
    return tweets


def parse_title_body(md_path: Path) -> tuple[str, str]:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = ""
    body_lines = []
    for i, line in enumerate(lines):
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            body_lines = lines[i + 1 :]
            break
    if not title:
        title = "SpreadSynth launch"
        body_lines = lines
    body = "\n".join(body_lines).strip()
    return title, body


def maybe_circuit_on_response(resp: requests.Response, context: str) -> None:
    txt = (resp.text or "")[:1200].lower()
    if resp.status_code in {401, 403, 429} or "captcha" in txt or "forbidden" in txt:
        raise CircuitBreak(f"{context} blocked (status={resp.status_code}). Circuit opened.")


def post_x_thread(cfg: EnvCfg, dry_run: bool = False) -> list[str]:
    tweets = parse_x_thread(X_THREAD_PATH)
    if dry_run:
        log(f"[DRY] X thread prepared ({len(tweets)} tweets)")
        return []

    if not all([cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_token_secret]):
        raise RuntimeError("X credentials missing in .env")

    try:
        from requests_oauthlib import OAuth1
    except Exception as e:
        raise RuntimeError("requests-oauthlib missing. Install: pip install requests-oauthlib") from e

    auth = OAuth1(cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_token_secret)
    endpoint = "https://api.x.com/2/tweets"

    ids: list[str] = []
    parent_id: str | None = None
    for idx, t in enumerate(tweets, start=1):
        payload: dict[str, Any] = {"text": t}
        if parent_id:
            payload["reply"] = {"in_reply_to_tweet_id": parent_id}
        r = requests.post(endpoint, json=payload, auth=auth, timeout=30)
        maybe_circuit_on_response(r, f"X tweet #{idx}")
        if r.status_code >= 300:
            raise RuntimeError(f"X tweet #{idx} failed: {r.status_code} {r.text[:300]}")
        tid = r.json().get("data", {}).get("id", "")
        if tid:
            ids.append(tid)
            parent_id = tid
        log(f"X tweet #{idx} posted: {tid or 'ok'}")
    return ids


def post_v2ex(cfg: EnvCfg, dry_run: bool = False) -> str:
    title, body = parse_title_body(V2EX_POST_PATH)
    if dry_run:
        log(f"[DRY] V2EX title: {title}")
        return ""

    if not cfg.v2ex_cookie:
        raise RuntimeError("V2EX_COOKIE missing in .env")

    s = requests.Session()
    s.headers.update({
        "Cookie": cfg.v2ex_cookie,
        "User-Agent": "SpreadSynth-Autopilot/0.1.0",
        "Referer": "https://www.v2ex.com/new/share",
    })

    new_url = "https://www.v2ex.com/new/share"
    r0 = s.get(new_url, timeout=25)
    maybe_circuit_on_response(r0, "V2EX preload")
    once_match = re.search(r'name="once" value="(\d+)"', r0.text)
    if not once_match:
        raise RuntimeError("V2EX once token not found (check cookie/session).")
    once = once_match.group(1)

    payload = {"once": once, "title": title[:120], "content": body}
    r1 = s.post(new_url, data=payload, timeout=25, allow_redirects=True)
    maybe_circuit_on_response(r1, "V2EX submit")

    if r1.status_code >= 300:
        raise RuntimeError(f"V2EX submit failed: {r1.status_code}")

    log("V2EX post submitted.")
    return r1.url


def post_hn(cfg: EnvCfg, dry_run: bool = False) -> str:
    title, body = parse_title_body(HN_POST_PATH)
    if dry_run:
        log(f"[DRY] HN title: {title}")
        return ""

    if not cfg.hn_cookie:
        raise RuntimeError("HN_COOKIE missing in .env")

    repo_url = "https://github.com/luanyajun666-cell/spreadsynth"
    s = requests.Session()
    s.headers.update({
        "Cookie": cfg.hn_cookie,
        "User-Agent": "SpreadSynth-Autopilot/0.1.0",
    })

    r0 = s.get("https://news.ycombinator.com/submit", timeout=25)
    maybe_circuit_on_response(r0, "HN preload")

    action_match = re.search(r'<form[^>]+action="(r\?fnid=[^"]+)"', r0.text)
    if not action_match:
        raise RuntimeError("HN fnid action not found (check cookie/session).")

    action_url = "https://news.ycombinator.com/" + action_match.group(1)
    payload = {"title": title[:80], "url": repo_url, "text": body[:12000]}
    r1 = s.post(action_url, data=payload, timeout=25, allow_redirects=True)
    maybe_circuit_on_response(r1, "HN submit")

    if r1.status_code >= 300:
        raise RuntimeError(f"HN submit failed: {r1.status_code}")

    log("HN post submitted.")
    return r1.url


def get_repo_stars(cfg: EnvCfg) -> int:
    if not cfg.gh_token:
        return -1
    headers = {
        "Authorization": f"token {cfg.gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    r = requests.get("https://api.github.com/repos/luanyajun666-cell/spreadsynth", headers=headers, timeout=25)
    if r.status_code >= 300:
        return -1
    return int(r.json().get("stargazers_count", 0))


def booster_x(cfg: EnvCfg, dry_run: bool = False) -> None:
    booster = (
        "Update: cross-source delay map just dropped.\n"
        "SG iron ore swap moved first, CN side lagged — SpreadScore 97.24 triggered red-alert.\n"
        "Repo: https://github.com/luanyajun666-cell/spreadsynth\n"
        "Chart: https://raw.githubusercontent.com/luanyajun666-cell/spreadsynth/main/assets/backtest-iron-ore-9724.png"
    )
    if dry_run:
        log("[DRY] booster tweet prepared")
        return

    if not all([cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_token_secret]):
        raise RuntimeError("X credentials missing for booster")

    try:
        from requests_oauthlib import OAuth1
    except Exception as e:
        raise RuntimeError("requests-oauthlib missing. Install: pip install requests-oauthlib") from e

    auth = OAuth1(cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_token_secret)
    r = requests.post("https://api.x.com/2/tweets", json={"text": booster}, auth=auth, timeout=30)
    maybe_circuit_on_response(r, "X booster")
    if r.status_code >= 300:
        raise RuntimeError(f"booster failed: {r.status_code} {r.text[:200]}")
    log("X booster posted.")


def notify(cfg: EnvCfg, text: str) -> None:
    # Telegram
    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage",
                json={"chat_id": cfg.telegram_chat_id, "text": text},
                timeout=15,
            )
        except Exception:
            pass

    # Feishu webhook
    if cfg.feishu_webhook:
        try:
            requests.post(cfg.feishu_webhook, json={"msg_type": "text", "content": {"text": text}}, timeout=15)
        except Exception:
            pass


def monitor_github_questions(cfg: EnvCfg, since_minutes: int = 15) -> list[str]:
    if not cfg.gh_token:
        return []

    headers = {
        "Authorization": f"token {cfg.gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    since = (datetime.utcnow() - timedelta(minutes=since_minutes)).isoformat() + "Z"

    drafts: list[str] = []

    # Recent issue comments
    url = "https://api.github.com/repos/luanyajun666-cell/spreadsynth/issues/comments"
    r = requests.get(url, headers=headers, params={"since": since, "per_page": 50}, timeout=30)
    if r.status_code < 300:
        for c in r.json():
            body = (c.get("body") or "").lower()
            if any(k in body for k in ["iron ore", "iron-ore", "formula", "weight", "d/t/c", "source"]):
                drafts.append(
                    "Draft reply (Chief Architect): Thanks for the sharp question. "
                    "Current iron-ore demo uses a historical SG-vs-CN snapshot for deterministic replay. "
                    "SpreadScore weights are 1.25D + 0.85T + 0.75C + 0.95A - 0.80K - 0.70F and can be calibrated per market regime."
                )

    return drafts


def run_due_actions(cfg: EnvCfg, state: dict[str, Any], dry_run: bool = False) -> None:
    done = state.setdefault("done", {})

    if due(SCHEDULE["x_thread"]) and not done.get("x_thread"):
        ids = post_x_thread(cfg, dry_run=dry_run)
        done["x_thread"] = True
        state["x_thread_ids"] = ids
        notify(cfg, "SpreadSynth autopilot: X thread posted.")

    if due(SCHEDULE["v2ex_post"]) and not done.get("v2ex_post"):
        url = post_v2ex(cfg, dry_run=dry_run)
        done["v2ex_post"] = True
        state["v2ex_url"] = url
        notify(cfg, f"SpreadSynth autopilot: V2EX submitted. {url}")

    if due(SCHEDULE["hn_post"]) and not done.get("hn_post"):
        url = post_hn(cfg, dry_run=dry_run)
        done["hn_post"] = True
        state["hn_url"] = url
        notify(cfg, f"SpreadSynth autopilot: HN submitted. {url}")

    # 10:00 booster condition
    if due(SCHEDULE["booster_check"]) and not state.get("booster_done"):
        stars = get_repo_stars(cfg)
        state["stars_at_booster_check"] = stars
        if stars != -1 and stars < 10:
            booster_x(cfg, dry_run=dry_run)
            state["booster_done"] = True
            notify(cfg, f"SpreadSynth autopilot: booster executed at stars={stars}.")
        else:
            state["booster_done"] = True


def run_monitor(cfg: EnvCfg, state: dict[str, Any]) -> None:
    last = state.get("last_monitor_ts")
    now = datetime.now(BJT)
    if last:
        prev = datetime.fromisoformat(last)
        if (now - prev).total_seconds() < 15 * 60:
            return

    drafts = monitor_github_questions(cfg, since_minutes=15)
    if drafts:
        msg = "\n\n".join(drafts)
        notify(cfg, f"SpreadSynth monitor draft replies:\n\n{msg}")
        log(f"Generated {len(drafts)} draft replies from recent comments.")

    state["last_monitor_ts"] = now.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="SpreadSynth autopilot posting engine")
    parser.add_argument("--env", default=str(ROOT / ".env"), help="Path to .env")
    parser.add_argument("--dry-run", action="store_true", help="No external posting, only simulation")
    parser.add_argument("--once", action="store_true", help="Run one cycle then exit")
    parser.add_argument("--interval-sec", type=int, default=60, help="Loop interval seconds")
    args = parser.parse_args()

    env_path = Path(args.env)
    cfg = load_env(env_path)

    state = load_state()
    state["date"] = datetime.now(BJT).strftime("%Y-%m-%d")

    log("Autopilot launch engine started.")

    try:
        while True:
            guard_and_unstage_env()
            run_due_actions(cfg, state, dry_run=args.dry_run)
            run_monitor(cfg, state)
            save_state(state)

            if args.once:
                break

            time.sleep(max(args.interval_sec, 15))

    except CircuitBreak as e:
        log(str(e))
        notify(cfg, f"🚨 SpreadSynth circuit break: {e}")
        save_state(state)
        return 2
    except Exception as e:
        log(f"Autopilot error: {e}")
        notify(cfg, f"🚨 SpreadSynth autopilot error: {e}")
        save_state(state)
        return 1

    log("Autopilot cycle finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
