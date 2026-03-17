# [分享创造] SpreadSynth：一个把“跨平台热点时间差”做成可执行信号的工具

大家好，我做了个新项目 **SpreadSynth**。  
它不是传统数据面板，而是一个“时间差套利引擎”：

- 同时监听 GitHub / Hacker News / X / RSS（后续可接更多源）
- 把不同来源的数据统一归一化
- 用 SpreadScore 给每个机会打分（0-100）
- 分数高了自动触发动作（提醒、战报、Webhook）

## 这个项目解决了什么痛点？

我自己平时会看很多渠道，经常遇到两个问题：

1. 热点在 A 平台已经爆了，B 平台还没扩散
2. 信息看到了，但无法快速判断“现在值不值得做”

SpreadSynth 的目标就是把“看起来很散的数据”变成“可以马上执行的动作”。

## 核心逻辑（简版）

SpreadScore 公式：

`100 * sigmoid(1.25D + 0.85T + 0.75C + 0.95A - 0.80K - 0.70F)`

- D：差值强度（是否有明显信息差）
- T：时效（窗口是否还在）
- C：可信度（多源校验）
- A：可执行性（是否能立刻触发动作）
- K：竞争拥挤度
- F：执行摩擦

## 一个有意思的细节（炫技）

当 SpreadScore > 90，界面会进入红色警报态，并自动生成“战报摘要”，同时模拟 Telegram 推送动效。  
（这个做出来之后，演示效果比静态图强很多）

## 1 分钟启动

```bash
git clone https://github.com/your-org/spreadsynth.git
cd spreadsynth
docker compose up --build
```

- Demo UI: http://localhost:8501
- API 文档: http://localhost:8000/docs

## 求建议

目前我最想听两类反馈：

1. 你希望优先接入哪些数据源？
2. 在你场景里，什么条件下你才会“马上执行”而不是“继续观察”？

项目地址（求 Star / Issue / PR）：  
https://github.com/your-org/spreadsynth
