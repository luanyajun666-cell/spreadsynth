from __future__ import annotations

from datetime import datetime, timezone

from .scorer import SignalEvent


def _ts(iso_utc: str) -> float:
    return datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).timestamp()


def generate_demo_events(entity: str = "iron-ore-sg-cn", wow: bool = True) -> list[SignalEvent]:
    """
    Historical data snapshot for demonstration.

    Case: 2026-03-04 SG iron ore swap moved first, CN side lagged because of session timing.
    Notes:
    - This is a fixed, hard-coded snapshot for deterministic demos.
    - Values are intentionally simplified into a compact replay set.
    """

    if entity in {"iron-ore-sg-cn", "iron-ore", "sg-cn"}:
        return [
            # SG lead signals (API + market feed)
            SignalEvent(
                source="api",
                timestamp=_ts("2026-03-04T01:10:00Z"),
                entity="iron-ore-sg-swap",
                metric_type="price",
                value=102.0,
                region="SG",
                latency_sec=20,
                parse_quality=0.98,
                url="https://example.com/sg-swap/2026-03-04-0110",
                tags=["alert", "trade"],
            ),
            SignalEvent(
                source="rss",
                timestamp=_ts("2026-03-04T01:25:00Z"),
                entity="iron-ore-sg-swap",
                metric_type="price",
                value=146.0,
                region="SG",
                latency_sec=35,
                parse_quality=0.92,
                url="https://example.com/sg-swap/2026-03-04-0125",
                tags=["alert", "publish"],
            ),
            SignalEvent(
                source="api",
                timestamp=_ts("2026-03-04T01:40:00Z"),
                entity="iron-ore-sg-swap",
                metric_type="price",
                value=258.0,
                region="SG",
                latency_sec=18,
                parse_quality=0.99,
                url="https://example.com/sg-swap/2026-03-04-0140",
                tags=["alert", "trade", "webhook"],
            ),
            # CN lag signals (crawler + social feed)
            SignalEvent(
                source="crawler",
                timestamp=_ts("2026-03-04T01:12:00Z"),
                entity="iron-ore-dce-future",
                metric_type="price",
                value=101.0,
                region="CN",
                latency_sec=240,
                parse_quality=0.82,
                url="https://example.cn/dce/2026-03-04-0112",
                tags=["draft"],
            ),
            SignalEvent(
                source="x",
                timestamp=_ts("2026-03-04T01:38:00Z"),
                entity="iron-ore-dce-future",
                metric_type="price",
                value=102.0,
                region="CN",
                latency_sec=180,
                parse_quality=0.80,
                url="https://example.cn/dce/2026-03-04-0138",
                tags=["draft", "publish"],
            ),
        ]

    # Fallback historical tech-topic lag snapshot (also deterministic)
    return [
        SignalEvent(
            source="github",
            timestamp=_ts("2026-03-06T08:00:00Z"),
            entity=entity,
            metric_type="mentions",
            value=180.0,
            region="US",
            latency_sec=40,
            parse_quality=0.95,
            url="https://github.com/trending",
            tags=["alert", "publish"],
        ),
        SignalEvent(
            source="github",
            timestamp=_ts("2026-03-06T08:20:00Z"),
            entity=entity,
            metric_type="mentions",
            value=360.0,
            region="US",
            latency_sec=35,
            parse_quality=0.95,
            url="https://github.com/trending",
            tags=["alert", "publish"],
        ),
        SignalEvent(
            source="rss",
            timestamp=_ts("2026-03-06T08:05:00Z"),
            entity=entity,
            metric_type="mentions",
            value=90.0,
            region="CN",
            latency_sec=140,
            parse_quality=0.84,
            url="https://example.cn/rss",
            tags=["draft"],
        ),
        SignalEvent(
            source="rss",
            timestamp=_ts("2026-03-06T08:25:00Z"),
            entity=entity,
            metric_type="mentions",
            value=118.0,
            region="CN",
            latency_sec=150,
            parse_quality=0.84,
            url="https://example.cn/rss",
            tags=["draft"],
        ),
    ]
