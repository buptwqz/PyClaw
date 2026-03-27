---
name: weather
description: 通过 http_get 工具查询天气信息。
always: false
---

# 天气查询

使用 `http_get` 工具请求以下 URL：

## wttr.in（推荐）

```
http_get(url="https://wttr.in/城市名?lang=zh&format=3")
```

示例：
- 北京：`https://wttr.in/Beijing?lang=zh&format=3`
- 上海：`https://wttr.in/Shanghai?lang=zh&format=3`
- 支持中文拼音或英文城市名
- `?format=3` 返回单行简洁格式：`城市: 天气 温度`
- `?1` 只看今天，`?0` 只看当前

## Open-Meteo（备用，纯 JSON）

先获取城市坐标，再查询：
```
http_get(url="https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true")
```

返回 JSON，包含温度、风速、天气代码。
