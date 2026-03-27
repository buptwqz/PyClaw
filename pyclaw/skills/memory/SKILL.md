---
name: memory
description: 双层记忆系统，支持长期事实存储和历史日志检索。
always: true
---

# 记忆

## 结构

- `memory/MEMORY.md` — 长期事实（偏好、用户信息、项目背景）。每次对话自动加载到上下文。
- `memory/HISTORY.md` — 追加式事件日志。不自动加载，格式：`[YYYY-MM-DD HH:MM] role: content`

## 可用工具

- `remember(key, value)` — 将一条事实写入长期记忆，若 key 已存在则更新。
- `recall()` — 读取所有已记住的长期事实。
- `search_history(keyword)` — 在历史日志中搜索关键词，返回最多 20 条。

## 使用规则

- 当用户分享偏好、姓名、习惯或重要背景时，**立即**调用 `remember` 保存。
- 在回答个人相关问题前，先调用 `recall` 检查已知信息。
- 需要回忆历史事件时，用 `search_history` 搜索日志。
- 不存储密码、证件号等敏感信息。
