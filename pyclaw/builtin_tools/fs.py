"""文件系统工具：读写工作区文件。"""
from pathlib import Path
from ..tools import tool

_WORKSPACE = Path.cwd()
_MAX = 8000


def _safe(path: str) -> Path:
    """确保路径在工作区内，防止路径穿越。"""
    p = (_WORKSPACE / path).resolve()
    if not str(p).startswith(str(_WORKSPACE.resolve())):
        raise ValueError("路径超出工作区范围")
    return p


@tool(description="读取工作区内的文件内容。", section="fs", profiles=["coding", "full"])
def read_file(path: str) -> str:
    """
    path: 相对于工作区的文件路径，例如 'README.md'
    """
    try:
        p = _safe(path)
        if not p.exists():
            return f"[错误] 文件不存在：{path}"
        text = p.read_text(encoding="utf-8", errors="replace")
        return text[:_MAX] + ("\n[内容已截断]" if len(text) > _MAX else "")
    except Exception as e:
        return f"[错误] {e}"


@tool(description="将内容写入工作区内的文件（覆盖）。", section="fs", profiles=["coding", "full"])
def write_file(path: str, content: str) -> str:
    """
    path: 相对于工作区的文件路径
    content: 要写入的文本内容
    """
    try:
        p = _safe(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"已写入：{path}（{len(content)} 字符）"
    except Exception as e:
        return f"[错误] {e}"


@tool(description="列出工作区目录内容。", section="fs", profiles=["coding", "full"])
def list_dir(path: str = ".") -> str:
    """
    path: 相对于工作区的目录路径，默认为根目录
    """
    try:
        p = _safe(path)
        items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = []
        for item in items[:50]:
            tag = "📄" if item.is_file() else "📁"
            lines.append(f"{tag} {item.name}")
        if len(list(p.iterdir())) > 50:
            lines.append("...(已截断)")
        return "\n".join(lines) or "（空目录）"
    except Exception as e:
        return f"[错误] {e}"
