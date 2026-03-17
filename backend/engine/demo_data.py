from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .scorer import SignalEvent


def generate_demo_events(entity: str = "mcp-agent", wow: bool = True) -> list[SignalEvent]:
    now = datetime.now(tz=timezone.utc)

    # US signals rise faster than CN => divergence opportunity
    us_base = [120, 180, 260, 390] if wow else [100, 130, 170, 210]
    cn_base = [80, 90, 105, 120] if wow else [80, 88, 95, 102]

    events: list[SignalEvent] = []
    for i, v in enumerate(us_base):
        ts = (now - timedelta(minutes=45 - i * 10)).timestamp()
        events.append(
            SignalEvent(
                source="github",
                timestamp=ts,
                entity=entity,
                metric_type="mentions",
                value=float(v),
                region="US",
                latency_sec=45,
                parse_quality=0.95,
                url=f"https://github.com/trending?q={entity}",
                tags=["alert", "publish"],
            )
        )

    for i, v in enumerate(cn_base):
        ts = (now - timedelta(minutes=44 - i * 10)).timestamp()
        events.append(
            SignalEvent(
                source="rss",
                timestamp=ts,
                entity=entity,
                metric_type="mentions",
                value=float(v),
                region="CN",
                latency_sec=120,
                parse_quality=0.84,
                url=f"https://example.cn/rss/{entity}",
                tags=["draft"],
            )
        )

    # Add one HN pulse event (high confidence)
    events.append(
        SignalEvent(
            source="hn",
            timestamp=(now - timedelta(minutes=5)).timestamp(),
            entity=entity,
            metric_type="upvotes",
            value=220.0,
            region="US",
            latency_sec=25,
            parse_quality=0.98,
            url="https://news.ycombinator.com/",
            tags=["alert", "webhook"],
        )
    )

    return events
