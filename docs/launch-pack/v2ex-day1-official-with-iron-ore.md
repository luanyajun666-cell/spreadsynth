# [分享创造] SpreadSynth：把“跨市场时差”变成可执行信号（附铁矿石实测 97.24）

大家好，开源了一个项目：**SpreadSynth**。

它不是单纯看板，而是一个“信息差/时差套利引擎”：
- 采集多源数据（API、RSS、爬虫）
- 统一归一化
- 用 SpreadScore 给机会打分
- 分数够高自动触发动作（提醒、战报、Webhook）

## 为什么值得试

我们刚做了一个极端场景自测：

**场景：** 新加坡铁矿石掉期快速拉升，而国内市场因开盘时差尚未完全反应。  
**输出：**
- D (差值强度) = **1.0**
- T (时效) = **0.9753**
- C (可信度) = **0.7908**
- A (可执行性) = **1.0**
- K (竞争拥挤度) = **0.0**
- F (执行摩擦) = **0.0854**
- SpreadScore = **97.24**
- Trigger = **red-alert**

这个结果说明：它不是“看起来很酷”，而是能把数据拆成可执行信号。

## 1 分钟启动

```bash
git clone https://github.com/your-org/spreadsynth.git
cd spreadsynth
docker compose up --build
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

## 目前进度

- 核心评分引擎已可跑
- 发布包（README / X / HN / V2EX）已完成
- 已加 4 小时 Watchtower（Issue / PR 自动首轮响应）

欢迎拍砖，尤其想听：
1) 你希望优先接入哪些市场数据源？
2) 在你场景里，Score 到多少你会“马上执行”？

仓库：  
https://github.com/your-org/spreadsynth
