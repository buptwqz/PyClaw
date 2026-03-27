---
name: memory
description: 双层记忆系统，支持长期事实存储和历史日志检索。
always: true
---

# 记忆

## 结构

- `memory/MEMORY.md` — 长期事实（偏好、用户信息、项目背景）。每次对话自动加载到上下文。
- `memory/HISTORY.md` — 追加式事件日志。不自动加载，格式：`[YYYY-MM-DD HH:MM] role: content`

## 使用规则

- 当用户分享偏好、姓名、习惯或重要背景时，立即调用 `remember` 工具保存。
- 在回答个人问题前，先调用 `recall` 检查已知信息。
- 不存储密码、证件号等敏感信息。
- 记忆条目格式：`- 键名: 值`
