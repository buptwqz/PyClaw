---
name: weather
description: 通过 wttr.in 或 Open-Meteo 查询天气信息。
always: false
---

# 天气查询

## wttr.in（推荐，无需 API Key）

```bash
curl -s "wttr.in/北京?lang=zh&format=3"
```

- 单位：`?m`（公制）
- 仅今天：`?1`，仅当前：`?0`
- 城市名支持中文拼音或英文，例如 `wttr.in/Shanghai`

## Open-Meteo（备用，JSON 格式）

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
```

先确定城市坐标，再查询。返回温度、风速、天气代码。

文档：https://open-meteo.com/en/docs
