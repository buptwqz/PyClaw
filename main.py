"""PyClaw 入口。

在此添加 @tool 工具。
技能文件放在 pyclaw/skills/<name>/SKILL.md（内置）或 skills/<name>/SKILL.md（自定义）。
身份/规范在 SOUL.md / AGENTS.md / USER.md 中定义（项目根目录优先）。
"""
import os
from pyclaw import tool
from pyclaw.memory import remember, recall
from pyclaw.qq import create_client


@tool(description="获取当前日期和时间（ISO 格式）。")
def get_time() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(description="计算数学表达式。")
def calculate(expression: str) -> str:
    """
    expression: Python 风格的数学表达式，例如 '2 + 3 * 4'
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"


# 注册记忆工具
tool(description="记住一条关于用户的事实。")(remember)
tool(description="查看所有已记住的事实。")(recall)


if __name__ == "__main__":
    print("PyClaw 启动中...")
    bot = create_client()
    bot.run(appid=os.getenv("QQ_APPID", ""), secret=os.getenv("QQ_SECRET", ""))
