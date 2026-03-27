---
name: exec
description: 通过 exec_command 工具在本地执行 shell 命令。
always: false
---

# 命令执行

使用 `exec_command` 工具运行本地命令：

```
exec_command(command="python --version")
exec_command(command="dir")          # Windows
exec_command(command="ls -la")       # Linux/Mac
```

## 约束

- 超时 30 秒，输出截断至 2000 字符
- 禁止危险命令：`rm -rf`、`format`、`dd if=`、`shutdown` 等
- 优先用于查询信息，不做破坏性操作
