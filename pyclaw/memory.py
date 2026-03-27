"""双层记忆系统

- memory/MEMORY.md  — 长期事实（偏好、用户信息、项目背景）。每次对话自动加载到 system prompt。
- memory/HISTORY.md — 追加式事件日志。不自动加载，可通过搜索工具查询。
"""
from datetime import datetime
from pathlib import Path

_MEMORY_DIR = Path.cwd() / "memory"


def _ensure_dir() -> Path:
    _MEMORY_DIR.mkdir(exist_ok=True)
    return _MEMORY_DIR


def load_memory() -> str:
    """读取 MEMORY.md 内容，用于注入 system prompt。"""
    f = _MEMORY_DIR / "MEMORY.md"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return ""


def remember(key: str, value: str) -> str:
    """将一条事实写入 MEMORY.md（以 key: value 格式）。

    key: 事实的名称，例如 '用户名' 或 '偏好语言'
    value: 事实的内容
    """
    d = _ensure_dir()
    mem_file = d / "MEMORY.md"
    content = mem_file.read_text(encoding="utf-8") if mem_file.exists() else ""
    # 若 key 已存在则替换，否则追加
    import re
    pattern = re.compile(rf"^- {re.escape(key)}:.*$", re.MULTILINE)
    new_line = f"- {key}: {value}"
    if pattern.search(content):
        content = pattern.sub(new_line, content)
    else:
        content = (content.rstrip() + "\n" + new_line + "\n").lstrip("\n")
    mem_file.write_text(content, encoding="utf-8")
    return f"已记住：{key} = {value}"


def recall() -> str:
    """读取所有已记住的事实。"""
    text = load_memory()
    return text if text else "暂无记忆。"


def log_history(role: str, content: str) -> None:
    """追加一条记录到 HISTORY.md（仅供内部调用）。"""
    d = _ensure_dir()
    hist_file = d / "HISTORY.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with hist_file.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {role}: {content[:200]}\n")
