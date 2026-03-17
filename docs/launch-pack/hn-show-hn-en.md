# Show HN: SpreadSynth — an open-source real-time signal processing engine for time-asymmetry detection

Hi HN,

I built **SpreadSynth**, an open-source real-time signal processing engine focused on **time-asymmetry detection** across heterogeneous sources (GitHub Trending, HN, X, RSS, and custom APIs).

The goal is not another dashboard. The goal is a deterministic pipeline that answers:

1. Is the divergence meaningful?
2. Is the timing window still valid?
3. Which action should be triggered now?

## Scoring model

`SpreadScore = 100 * sigmoid(1.25D + 0.85T + 0.75C + 0.95A - 0.80K - 0.70F)`

Where:
- `D` divergence strength
- `T` timeliness decay
- `C` confidence (source reliability + parser quality + cross-source agreement)
- `A` actionability
- `K` saturation/competition
- `F` execution friction

## Technical structure

- Multi-source normalization layer (`API/RSS/crawler -> unified event schema`)
- FastAPI backend (`/api/score`, `/api/demo/opportunity`)
- Streamlit demo UI (radar core + trigger panel + replay hints)
- Docker Compose one-command startup

## Deterministic demo data

To avoid random output, demo events use a fixed historical snapshot:

- SG-side iron ore swap lead signal
- CN-side lagged response snapshot

This keeps the run reproducible and easy to validate.

## Run locally

```bash
git clone https://github.com/luanyajun666-cell/spreadsynth.git
cd spreadsynth
docker compose up --build
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

Repo: https://github.com/luanyajun666-cell/spreadsynth

Feedback I care about:
- Better divergence definitions for cross-region topic propagation
- Calibration strategy for noisy social sources
- Practical trigger/action contracts for production use
