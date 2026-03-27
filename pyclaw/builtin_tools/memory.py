"""记忆工具：长期/会话记忆操作。"""
from ..tools import tool
from ..memory import (
    remember as _remember,
    recall as _recall,
    forget as _forget,
    search_history as _search,
    clear_session as _clear,
)


@tool(description="记住一条关于用户的事实（key/value）。", section="memory", profiles=["minimal", "coding", "messaging", "full"])
def remember(key: str, value: str) -> str:
    """
    key: 事实名称，例如 '用户名'
    value: 事实内容
    """
    return _remember(key, value)


@tool(description="查看所有已记住的长期事实。", section="memory", profiles=["minimal", "coding", "messaging", "full"])
def recall() -> str:
    return _recall()


@tool(description="删除一条已记住的事实。", section="memory", profiles=["coding", "messaging", "full"])
def forget(key: str) -> str:
    """
    key: 要删除的事实名称
    """
    return _forget(key)


@tool(description="在历史对话日志中搜索关键词，返回最近 20 条匹配。", section="memory", profiles=["coding", "messaging", "full"])
def search_history(keyword: str) -> str:
    """
    keyword: 搜索关键词
    """
    return _search(keyword)


@tool(description="清除指定会话的对话历史。", section="memory", profiles=["full"])
def clear_session(key: str) -> str:
    """
    key: 会话标识符，例如 'c2c_openid'
    """
    return _clear(key)
