# X (Twitter) Thread Script (5 Tweets) — Final

## Tweet 1 (爆点)
We built a cyberpunk radar for signal arbitrage.

Meet **SpreadSynth**: a real-time time-asymmetry engine across GitHub / HN / X / RSS.

Live self-test (SG iron ore swap vs CN lag): **SpreadScore 97.24** → **RED-ALERT**.

(Attach image: `assets/backtest-iron-ore-9724.png`)

## Tweet 2
Most dashboards tell you what happened.

SpreadSynth tells you what to do **now**:
- detect divergence
- score timing window
- trigger action automatically

Score model:
`D + T + C + A - K - F`

## Tweet 3
Iron ore extreme-case breakdown from our run:
- D=1.0
- T=0.9753
- C=0.7908
- A=1.0
- K=0.0
- F=0.0854

Final: **97.24** (red-alert)

## Tweet 4
1-minute run:
```bash
git clone https://github.com/luanyajun666-cell/spreadsynth.git
cd spreadsynth
docker compose up --build
```
UI: http://localhost:8501
API: http://localhost:8000/docs

## Tweet 5 (CTA)
If you build in automation / data-viz / quant-like workflows, this is for you.

⭐ GitHub: https://github.com/luanyajun666-cell/spreadsynth

Drop feedback / PRs. Next release ships iron ore real-time API integration.
