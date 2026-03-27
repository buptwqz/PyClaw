"""System prompt 构建器 — 组装 SOUL.md + AGENTS.md + 技能 + 用户偏好 + 记忆。"""
from pathlib import Path

from .skills import SkillsLoader
from .memory import load_memory

TEMPLATES_DIR = Path(__file__).parent / "templates"


class ContextBuilder:
    BOOTSTRAP_FILES = ["SOUL.md", "AGENTS.md"]

    def __init__(self, workspace: Path = Path.cwd()):
        self.workspace = workspace
        self.skills = SkillsLoader()

    def _load_template(self, filename: str) -> str:
        # workspace 文件优先于内置模板
        ws = self.workspace / filename
        if ws.exists():
            return ws.read_text(encoding="utf-8")
        builtin = TEMPLATES_DIR / filename
        if builtin.exists():
            return builtin.read_text(encoding="utf-8")
        return ""

    def build_system_prompt(self, extra_skill_names: list[str] | None = None) -> str:
        """构建完整 system prompt。

        顺序：
          1. SOUL.md     — 人格/身份
          2. AGENTS.md   — 行为规范
          3. USER.md     — 用户偏好（仅 workspace）
          4. MEMORY.md   — 长期记忆（自动注入）
          5. always 技能 — always: true 的技能
          6. 额外技能    — 本次显式请求的技能
        """
        parts: list[str] = []

        for fname in self.BOOTSTRAP_FILES:
            content = self._load_template(fname)
            if content:
                parts.append(content.strip())

        # USER.md 仅 workspace
        user_md = self.workspace / "USER.md"
        if user_md.exists():
            parts.append(user_md.read_text(encoding="utf-8").strip())

        # 长期记忆
        memory_text = load_memory()
        if memory_text:
            parts.append(f"## 记忆\n\n{memory_text}")

        # always 技能 + 额外技能
        always = self.skills.get_always_skills()
        all_skill_names = list(dict.fromkeys(always + (extra_skill_names or [])))
        for name in all_skill_names:
            body = self.skills.get_body(name)
            if body:
                parts.append(f"## 技能：{name}\n\n{body}")

        return "\n\n".join(parts)
