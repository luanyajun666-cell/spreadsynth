# Show HN: SpreadSynth — a real-time signal arbitrage engine for cross-platform trend divergence

Hi HN,

I built **SpreadSynth**, a small system that tracks trend/interest divergence across multiple sources (GitHub Trending, Hacker News, X, RSS, and custom APIs) and turns it into an execution-ready score.

The project motivation was simple: dashboards are good at observability, but weak at actionability. I wanted a pipeline that answers:

1. Is this divergence real?
2. Is the timing window still open?
3. Should I execute now or ignore?

## Scoring model

`SpreadScore = 100 * sigmoid(1.25D + 0.85T + 0.75C + 0.95A - 0.80K - 0.70F)`

Where:
- `D` divergence strength
- `T` timeliness decay
- `C` confidence (source reliability + parser quality + cross-source agreement)
- `A` actionability
- `K` saturation/competition
- `F` execution friction

## Technical notes

- Multi-source normalization layer (API/RSS/crawler -> unified event schema)
- FastAPI backend (scoring + demo endpoints)
- Streamlit demo UI (radar-like panel, breakdown, replay panel)
- Docker Compose one-command startup

A small "wow" behavior is included in demo mode: if score > 90, UI switches to red-alert state and auto-generates a short battle report with a simulated Telegram push animation.

## Run locally

```bash
git clone https://github.com/your-org/spreadsynth.git
cd spreadsynth
docker compose up --build
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

Repo: https://github.com/your-org/spreadsynth

Feedback welcome, especially on:
- scoring calibration for noisy sources
- better divergence definitions for cross-region trends
- practical automation actions after trigger
