from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from engine.demo_data import generate_demo_events
from engine.scorer import SignalEvent, SpreadScorer

app = FastAPI(title="SpreadSynth API", version="0.1.0")
scorer = SpreadScorer()


class ScoreRequestEvent(BaseModel):
    source: Literal["api", "rss", "crawler", "github", "hn", "x", "other"]
    timestamp: float
    entity: str
    metric_type: Literal["mentions", "stars", "upvotes", "search_volume", "price"]
    value: float
    region: str = "GLOBAL"
    confidence: float | None = None
    latency_sec: float = 60.0
    parse_quality: float = 1.0
    url: str = ""
    tags: list[str] = Field(default_factory=list)


class ScoreRequest(BaseModel):
    lead_region: str = "US"
    lag_region: str = "CN"
    events: list[ScoreRequestEvent]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/demo/opportunity")
def demo_opportunity(entity: str = "mcp-agent", wow: bool = True):
    events = generate_demo_events(entity=entity, wow=wow)
    breakdown = scorer.score(events)
    return {
        "entity": entity,
        "score": asdict(breakdown),
        "events": [asdict(e) for e in events],
    }


@app.post("/api/score")
def calculate_score(body: ScoreRequest):
    events = [SignalEvent(**e.model_dump()) for e in body.events]
    breakdown = scorer.score(events, lead_region=body.lead_region, lag_region=body.lag_region)
    return {"score": asdict(breakdown)}
