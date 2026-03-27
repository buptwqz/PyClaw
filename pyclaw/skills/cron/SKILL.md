---
name: cron
description: 管理定时任务和提醒，支持一次性、周期性和 cron 表达式调度。
always: false
---

# 定时任务

使用 `cron_add`、`cron_list`、`cron_remove` 工具管理定时任务。

## 三种模式

1. **reminder** — 到时间直接发消息提醒用户
2. **task** — 到时间由 AI 执行任务描述，并将结果发送给用户

## 三种调度方式

### 1. 指定时刻（一次性）
```
cron_add(message="提醒我开会", at="2025-06-01T09:00:00", mode="reminder")
```

### 2. 固定间隔
```
cron_add(message="提醒我喝水", every_seconds=3600, mode="reminder")
cron_add(message="检查 GitHub 有没有新 Issue 并汇报", every_seconds=86400, mode="task")
```

### 3. Cron 表达式
```
cron_add(message="早报：查询今日天气和新闻", cron_expr="0 8 * * *", mode="task")
cron_add(message="每周报告", cron_expr="0 9 * * 1", mode="task")
```

## 常用 Cron 表达式

| 表达式 | 含义 |
|---|---|
| `0 8 * * *` | 每天早上 8 点 |
| `0 9 * * 1-5` | 工作日早上 9 点 |
| `0 */2 * * *` | 每 2 小时 |
| `30 12 * * *` | 每天中午 12:30 |

## 管理任务
```
cron_list()           # 查看所有任务
cron_remove(job_id)   # 删除任务
```
