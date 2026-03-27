"""PyClaw 入口。

内置工具已自动加载（builtin_tools/）。
在此添加项目专属工具，或保持空白。
Skill 文件放 skills/<name>/SKILL.md。
MCP server 配置在 mcp_servers.json。
"""
import os
import asyncio
from pyclaw import tool
from pyclaw.qq import create_client
from pyclaw import mcp


# ── 在此添加你的自定义工具 ──────────────────────────────────────────────────────
# 示例：
# @tool(description="查询订单状态。", section="messaging", profiles=["full"])
# def check_order(order_id: str) -> str:
#     return f"订单 {order_id} 状态：已发货"


# ── 启动 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 先建立事件循环，让 botpy 和 asyncio.run 共用同一个循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 在同一个循环内加载 MCP
    loop.run_until_complete(mcp.load_mcp_servers())

    print("PyClaw 启动中...")
    bot = create_client()
    bot.run(appid=os.getenv("QQ_APPID", ""), secret=os.getenv("QQ_SECRET", ""))
