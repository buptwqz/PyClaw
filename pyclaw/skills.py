"""Skills loader — skills are markdown files (SKILL.md) with YAML frontmatter.

Each skill teaches the agent how to perform a capability.
Skills are loaded from:
  1. pyclaw/skills/  (builtin)
  2. skills/         (workspace, user-defined, higher priority)
"""
import re
from pathlib import Path

BUILTIN_SKILLS_DIR = Path(__file__).parent / "skills"
WORKSPACE_SKILLS_DIR = Path.cwd() / "skills"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown. Returns (meta, body)."""
    if not content.startswith("---"):
        return {}, content
    match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    if not match:
        return {}, content
    meta: dict = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            val = v.strip().strip("'\"")
            if val.lower() == "true":
                val = True  # type: ignore
            elif val.lower() == "false":
                val = False  # type: ignore
            meta[k.strip()] = val
    body = content[match.end():]
    return meta, body


class SkillsLoader:
    def __init__(
        self,
        builtin_dir: Path = BUILTIN_SKILLS_DIR,
        workspace_dir: Path = WORKSPACE_SKILLS_DIR,
    ):
        self.builtin_dir = builtin_dir
        self.workspace_dir = workspace_dir

    def _scan_dir(self, base: Path, source: str) -> list[dict]:
        skills = []
        if not base.exists():
            return skills
        for skill_dir in sorted(base.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skills.append({"name": skill_dir.name, "path": skill_file, "source": source})
        return skills

    def list_skills(self) -> list[dict]:
        """Return all skills; workspace overrides builtin by name."""
        workspace = self._scan_dir(self.workspace_dir, "workspace")
        builtin = self._scan_dir(self.builtin_dir, "builtin")
        ws_names = {s["name"] for s in workspace}
        return workspace + [s for s in builtin if s["name"] not in ws_names]

    def load_skill(self, name: str) -> str | None:
        """Load raw SKILL.md content for a named skill."""
        for s in self.list_skills():
            if s["name"] == name:
                return s["path"].read_text(encoding="utf-8")
        return None

    def get_metadata(self, name: str) -> dict:
        content = self.load_skill(name)
        if not content:
            return {}
        meta, _ = _parse_frontmatter(content)
        return meta

    def get_body(self, name: str) -> str:
        content = self.load_skill(name)
        if not content:
            return ""
        _, body = _parse_frontmatter(content)
        return body.strip()

    def get_always_skills(self) -> list[str]:
        """Return names of skills with always: true."""
        return [s["name"] for s in self.list_skills() if self.get_metadata(s["name"]).get("always") is True]
