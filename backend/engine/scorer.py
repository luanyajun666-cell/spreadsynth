from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import exp, log1p
from statistics import mean
from typing import Iterable, Literal

SourceKind = Literal["api", "rss", "crawler", "github", "hn", "x", "other"]
MetricKind = Literal["mentions", "stars", "upvotes", "search_volume", "price"]


SOURCE_BASE_CONFIDENCE: dict[SourceKind, float] = {
    "api": 0.92,
    "github": 0.90,
    "hn": 0.87,
    "x": 0.78,
    "rss": 0.74,
    "crawler": 0.66,
    "other": 0.60,
}


@dataclass
class SignalEvent:
    source: SourceKind
    timestamp: float  # unix seconds
    entity: str
    metric_type: MetricKind
    value: float
    region: str = "GLOBAL"
    confidence: float | None = None
    latency_sec: float = 60.0
    parse_quality: float = 1.0
    url: str = ""
    tags: list[str] | None = None


@dataclass
class ScoreBreakdown:
    D: float
    T: float
    C: float
    A: float
    K: float
    F: float
    score: float
    trigger: str


class SpreadScorer:
    """
    SpreadScore = 100 * sigmoid(1.25D + 0.85T + 0.75C + 0.95A - 0.80K - 0.70F)
    """

    def __init__(self, half_life_minutes: float = 90.0):
        self.half_life_minutes = half_life_minutes

    @staticmethod
    def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, x))

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x >= 0:
            z = exp(-x)
            return 1 / (1 + z)
        z = exp(x)
        return z / (1 + z)

    def normalize_event(self, e: SignalEvent, cross_source_agreement: float = 0.7) -> dict:
        """Normalize a multi-source event into model-ready values."""
        base_conf = SOURCE_BASE_CONFIDENCE.get(e.source, SOURCE_BASE_CONFIDENCE["other"])
        parse_quality = self._clip(e.parse_quality)
        cross = self._clip(cross_source_agreement)

        if e.confidence is None:
            confidence = 0.5 * base_conf + 0.3 * parse_quality + 0.2 * cross
        else:
            confidence = self._clip(e.confidence)

        # Metric normalization to comparable space
        if e.metric_type in {"mentions", "stars", "upvotes", "search_volume"}:
            normalized_value = log1p(max(e.value, 0.0))
        elif e.metric_type == "price":
            # If price-like, keep relative magnitude bounded
            normalized_value = self._clip(abs(e.value) / 100.0, 0.0, 3.0)
        else:
            normalized_value = log1p(max(e.value, 0.0))

        return {
            "source": e.source,
            "entity": e.entity,
            "region": e.region,
            "metric_type": e.metric_type,
            "timestamp": e.timestamp,
            "normalized_value": normalized_value,
            "confidence": confidence,
            "latency_sec": max(0.0, e.latency_sec),
            "has_url": 1.0 if e.url else 0.0,
            "tags": e.tags or [],
        }

    def _growth(self, values: list[float]) -> float:
        if not values:
            return 0.0
        if len(values) == 1:
            return values[0]
        first = max(values[0], 1e-6)
        last = values[-1]
        return (last - first) / abs(first)

    def score(
        self,
        events: Iterable[SignalEvent],
        lead_region: str = "US",
        lag_region: str = "CN",
        now_ts: float | None = None,
    ) -> ScoreBreakdown:
        rows = [self.normalize_event(e) for e in events]
        if not rows:
            return ScoreBreakdown(0, 0, 0, 0, 1, 1, 0.0, "no-data")

        now_ts = now_ts or datetime.now(tz=timezone.utc).timestamp()

        # Split by region for divergence
        lead_vals = [r["normalized_value"] for r in rows if r["region"].upper() == lead_region.upper()]
        lag_vals = [r["normalized_value"] for r in rows if r["region"].upper() == lag_region.upper()]

        if not lead_vals:
            lead_vals = [r["normalized_value"] for r in rows]
        if not lag_vals:
            lag_vals = [mean([r["normalized_value"] for r in rows])]

        g_lead = self._growth(lead_vals)
        g_lag = self._growth(lag_vals)

        # D: divergence strength, mapped to [0,1]
        raw_div = g_lead - g_lag
        D = self._clip(0.5 + 0.5 * (raw_div / (abs(g_lag) + 1.0)))

        # T: timeliness decay
        newest_age_min = min(max((now_ts - r["timestamp"]) / 60.0, 0.0) for r in rows)
        T = exp(-newest_age_min / self.half_life_minutes)
        T = self._clip(T)

        # C: confidence
        C = self._clip(mean(r["confidence"] for r in rows))

        # A: actionability (URLs + actionable tags)
        actionable_tags = {"alert", "trade", "launch", "publish", "webhook", "draft"}
        tag_hit_ratio = mean(
            1.0 if any(t.lower() in actionable_tags for t in r["tags"]) else 0.0 for r in rows
        )
        url_ratio = mean(r["has_url"] for r in rows)
        A = self._clip(0.6 * url_ratio + 0.4 * tag_hit_ratio)

        # K: saturation/competition (more duplicate noisy signals => higher K)
        source_count = len({r["source"] for r in rows})
        density = len(rows) / max(source_count, 1)
        K = self._clip((density - 1) / 6)  # density 1..7 -> 0..1

        # F: friction (latency and missing structure)
        avg_latency = mean(r["latency_sec"] for r in rows)
        latency_penalty = self._clip(avg_latency / 900.0)  # 15 min -> high friction
        missing_url_penalty = 1.0 - url_ratio
        F = self._clip(0.65 * latency_penalty + 0.35 * missing_url_penalty)

        linear = 1.25 * D + 0.85 * T + 0.75 * C + 0.95 * A - 0.80 * K - 0.70 * F
        score = round(100.0 * self._sigmoid(linear), 2)

        if score >= 90:
            trigger = "red-alert"
        elif score >= 75:
            trigger = "execute-now"
        elif score >= 55:
            trigger = "watch"
        else:
            trigger = "archive"

        return ScoreBreakdown(D=round(D, 4), T=round(T, 4), C=round(C, 4), A=round(A, 4), K=round(K, 4), F=round(F, 4), score=score, trigger=trigger)

    @staticmethod
    def to_dict(breakdown: ScoreBreakdown) -> dict:
        return asdict(breakdown)


def _simulate_iron_ore_lag_arbitrage() -> list[SignalEvent]:
    """
    极端机会场景：
    新加坡铁矿石掉期价格快速拉升，而国内大商所（CN）由于开盘时差尚未反应。
    """
    now_ts = datetime.now(tz=timezone.utc).timestamp()

    return [
        # SG side: strong move, low latency, actionable
        SignalEvent(
            source="api",
            timestamp=now_ts - 600,
            entity="iron-ore-swap",
            metric_type="price",
            value=102.0,
            region="SG",
            latency_sec=18,
            parse_quality=0.98,
            url="https://example.com/sg-swap/t0",
            tags=["alert", "trade"],
        ),
        SignalEvent(
            source="rss",
            timestamp=now_ts - 180,
            entity="iron-ore-swap",
            metric_type="price",
            value=258.0,
            region="SG",
            latency_sec=35,
            parse_quality=0.91,
            url="https://example.com/sg-swap/t1",
            tags=["alert", "webhook"],
        ),
        # CN side: near-flat response (market lag)
        SignalEvent(
            source="crawler",
            timestamp=now_ts - 660,
            entity="dce-iron-ore-future",
            metric_type="price",
            value=101.0,
            region="CN",
            latency_sec=240,
            parse_quality=0.82,
            url="https://example.com/dce/t0",
            tags=["draft"],
        ),
        SignalEvent(
            source="x",
            timestamp=now_ts - 210,
            entity="dce-iron-ore-future",
            metric_type="price",
            value=102.0,
            region="CN",
            latency_sec=180,
            parse_quality=0.80,
            url="https://example.com/dce/t1",
            tags=["publish"],
        ),
    ]


def _print_breakdown(b: ScoreBreakdown) -> None:
    print("\\n=== SpreadSynth Self-Test (Iron Ore Lag Arbitrage) ===")
    print(f"D (Divergence)  : {b.D}")
    print(f"T (Timeliness)  : {b.T}")
    print(f"C (Confidence)  : {b.C}")
    print(f"A (Actionability): {b.A}")
    print(f"K (Saturation)  : {b.K}")
    print(f"F (Friction)    : {b.F}")
    print(f"SpreadScore     : {b.score}")
    print(f"Trigger         : {b.trigger}")


def main() -> int:
    scorer = SpreadScorer(half_life_minutes=120.0)
    events = _simulate_iron_ore_lag_arbitrage()
    result = scorer.score(events, lead_region="SG", lag_region="CN")
    _print_breakdown(result)

    if result.score >= 90 and result.trigger == "red-alert":
        print("Self-test verdict: PASS (score >= 90 and red-alert triggered)")
        return 0

    print("Self-test verdict: FAIL (score threshold or trigger not met)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
