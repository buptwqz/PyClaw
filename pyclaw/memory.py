"""三层记忆系统

层级：
  1. 短期记忆（in-memory）  — 当前进程内，重启丢失
  2. 会话记忆（持久化）     — memory/sessions/<key>.json，跨重启保持对话上下文
  3. 长期记忆               — memory/MEMORY.md，LLM提取的关键事实，注入 system prompt
  4. 历史日志               — memory/HISTORY.md，追加式完整流水账

记忆压缩：
  会话消息数超过 COMPRESS_THRESHOLD 时，调用 LLM 生成摘要替换旧消息。
"""
import json
import re
from datetime import datetime
from pathlib import Path

_MEMORY_DIR = Path.cwd() / "memory"

COMPRESS_THRESHOLD = 30  # 超过此消息数触发压缩
KEEP_RECENT = 10          # 压缩后保留最近 N 条


def _ensure_dir() -> Path:
    _MEMORY_DIR.mkdir(exist_ok=True)
    (_MEMORY_DIR / "sessions").mkdir(exist_ok=True)
    return _MEMORY_DIR


# ── 长期记忆 MEMORY.md ────────────────────────────────────────────────────────

def load_memory() -> str:
    """读取 MEMORY.md，注入 system prompt。"""
    f = _MEMORY_DIR / "MEMORY.md"
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def remember(key: str, value: str) -> str:
    """将一条事实写入长期记忆。若 key 已存在则更新。

    key: 事实名称，例如 '用户名' 或 '偏好语言'
    value: 事实内容
    """
    d = _ensure_dir()
    mem_file = d / "MEMORY.md"
    content = mem_file.read_text(encoding="utf-8") if mem_file.exists() else ""
    pattern = re.compile(rf"^- {re.escape(key)}:.*$", re.MULTILINE)
    new_line = f"- {key}: {value}"
    if pattern.search(content):
        content = pattern.sub(new_line, content)
    else:
        content = (content.rstrip() + "\n" + new_line + "\n").lstrip("\n")
    mem_file.write_text(content, encoding="utf-8")
    return f"已记住：{key} = {value}"


def forget(key: str) -> str:
    """从长期记忆中删除一条事实。

    key: 要删除的事实名称
    """
    mem_file = _MEMORY_DIR / "MEMORY.md"
    if not mem_file.exists():
        return f"未找到记忆：{key}"
    content = mem_file.read_text(encoding="utf-8")
    pattern = re.compile(rf"^- {re.escape(key)}:.*\n?", re.MULTILINE)
    new_content = pattern.sub("", content)
    if new_content == content:
        return f"未找到记忆：{key}"
    mem_file.write_text(new_content, encoding="utf-8")
    return f"已删除记忆：{key}"


def recall() -> str:
    """读取所有已记住的长期事实。"""
    text = load_memory()
    return text if text else "暂无长期记忆。"


# ── 会话记忆 sessions/<key>.json ──────────────────────────────────────────────

def _session_file(key: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", key)
    return _MEMORY_DIR / "sessions" / f"{safe}.json"


def load_session(key: str) -> list[dict]:
    """加载持久化会话历史。"""
    f = _session_file(key)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_session(key: str, messages: list[dict]) -> None:
    """持久化会话历史。"""
    _ensure_dir()
    _session_file(key).write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_session(key: str) -> str:
    """清除某个会话的历史记录。

    key: 会话 key，例如 'c2c_xxx' 或 'group_xxx'
    """
    f = _session_file(key)
    if f.exists():
        f.unlink()
        return f"已清除会话：{key}"
    return f"会话不存在：{key}"


# ── 历史日志 HISTORY.md ───────────────────────────────────────────────────────

def log_history(role: str, content: str) -> None:
    """追加一条记录到 HISTORY.md（内部调用）。"""
    d = _ensure_dir()
    hist_file = d / "HISTORY.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    safe = content[:500].replace("\n", " ")
    with hist_file.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {role}: {safe}\n")


def search_history(keyword: str) -> str:
    """在历史对话日志中搜索包含关键词的记录，返回最多 20 条。

    keyword: 要搜索的关键词
    """
    hist_file = _MEMORY_DIR / "HISTORY.md"
    if not hist_file.exists():
        return "历史记录为空。"
    lines = hist_file.read_text(encoding="utf-8").splitlines()
    kw = keyword.lower()
    matched = [l for l in lines if kw in l.lower()]
    return "\n".join(matched[-20:]) if matched else f"未找到包含 '{keyword}' 的历史记录。"


# ── 记忆压缩 ──────────────────────────────────────────────────────────────────

async def compress_session(key: str, messages: list[dict], llm_chat_fn) -> list[dict]:
    """当会话消息超过阈值时，调用 LLM 生成摘要，压缩旧消息。"""
    if len(messages) <= COMPRESS_THRESHOLD:
        return messages

    to_compress = messages[:-KEEP_RECENT]
    recent = messages[-KEEP_RECENT:]

    prompt = [
        {"role": "system", "content": (
            "你是对话摘要助手。请将以下对话历史压缩为简洁摘要，"
            "保留所有重要信息、决定和事实。输出格式：纯文本摘要，100字以内。"
        )},
        {"role": "user", "content": "\n".join(
            f"{m['role']}: {m['content']}" for m in to_compress if m.get("content")
        )},
    ]
    try:
        result = await llm_chat_fn(prompt)
        summary = result.get("content", "").strip()
        if summary:
            compressed = [{"role": "system", "content": f"[对话摘要]\n{summary}"}] + recent
            save_session(key, compressed)
            return compressed
    except Exception:
        pass
    return messages


# ── 自动整理长期记忆 ──────────────────────────────────────────────────────────

async def auto_consolidate(user_input: str, reply: str, llm_chat_fn) -> None:
    """对话结束后，调用 LLM 提取新事实并更新 MEMORY.md。"""
    existing = load_memory()
    prompt = [
        {"role": "system", "content": (
            "你是记忆整理助手。根据下面的对话，提取值得长期记住的用户事实（偏好、姓名、习惯、重要背景等）。"
            "如果没有新事实，只输出 <no_update>。"
            "否则每行输出一条，格式：- key: value。不要输出其他内容。"
            f"\n\n已有记忆：\n{existing or '（无）'}"
        )},
        {"role": "user", "content": f"用户：{user_input}\n助手：{reply}"},
    ]
    try:
        result = await llm_chat_fn(prompt)
        text = result.get("content", "").strip()
        if text and "<no_update>" not in text:
            for line in text.splitlines():
                m = re.match(r"^-\s*(.+?):\s*(.+)$", line.strip())
                if m:
                    remember(m.group(1).strip(), m.group(2).strip())
    except Exception:
        pass
