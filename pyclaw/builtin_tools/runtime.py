"""运行时工具：时间、计算、命令执行。"""
import re
import asyncio
from datetime import datetime
from ..tools import tool

_BLOCKED = re.compile(
    r"(rm\s+-rf|format\s+[a-z]:|\.exe\s*&&|dd\s+if=|shutdown|del\s+/[sqf])",
    re.IGNORECASE,
)


@tool(description="获取当前日期和时间。", section="runtime", profiles=["minimal", "coding", "messaging", "full"])
def get_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(description="计算数学表达式。", section="runtime", profiles=["coding", "messaging", "full"])
def calculate(expression: str) -> str:
    """
    expression: Python 风格数学表达式，例如 '2 ** 10'
    """
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算错误：{e}"


@tool(description="在本地执行 shell 命令，返回输出（最多 2000 字符）。", section="runtime", profiles=["coding", "full"])
async def exec_command(command: str) -> str:
    """
    command: 要执行的 shell 命令
    """
    if _BLOCKED.search(command):
        return "[拒绝] 该命令被安全策略禁止。"
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        text = out.decode("utf-8", errors="replace")
        return text[:2000] + ("\n[输出已截断]" if len(text) > 2000 else "")
    except asyncio.TimeoutError:
        return "[超时] 命令执行超过 30 秒。"
    except Exception as e:
        return f"[错误] {e}"
