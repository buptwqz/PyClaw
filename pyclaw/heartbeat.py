"""心跳服务 — 定期唤醒 agent 检查周期任务。

设计（参考 nanobot）：
  Phase 1（决策）：读取 HEARTBEAT.md，用 LLM 判断是否有待执行任务。
  Phase 2（执行）：仅当 Phase 1 返回 run 时，执行任务并通过回调发送结果。
"""
import asyncio
from pathlib import Path
from .config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL
import httpx

_HEARTBEAT_FILE = Path.cwd() / "HEARTBEAT.md"
_DEFAULT_INTERVAL = 30 * 60  # 30 分钟

_DECIDE_TOOL = [{
    "type": "function",
    "function": {
        "name": "heartbeat",
        "description": "审阅任务后报告决策。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["skip", "run"],
                    "description": "skip=无需执行，run=有待办任务",
                },
                "tasks": {
                    "type": "string",
                    "description": "待执行任务的自然语言描述（action=run 时必填）",
                },
            },
            "required": ["action"],
        },
    },
}]


class HeartbeatService:
    """定期心跳服务。"""

    def __init__(
        self,
        on_execute,        # async (task_desc: str) -> str
        on_notify,         # async (result: str) -> None
        interval_s: int = _DEFAULT_INTERVAL,
    ):
        self.on_execute = on_execute
        self.on_notify = on_notify
        self.interval_s = interval_s
        self._task: asyncio.Task | None = None
        self._http = httpx.AsyncClient(
            base_url=QWEN_BASE_URL, timeout=60, trust_env=False
        )

    def start(self) -> None:
        """启动心跳循环（后台任务）。"""
        self._task = asyncio.create_task(self._loop())
        print(f"[Heartbeat] 已启动，间隔 {self.interval_s // 60} 分钟")

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval_s)
            await self._tick()

    async def trigger_now(self) -> str | None:
        """手动触发一次心跳。"""
        return await self._tick()

    async def _tick(self) -> str | None:
        content = self._read_file()
        if not content:
            return None
        print("[Heartbeat] 检查任务...")
        try:
            action, tasks = await self._decide(content)
            if action != "run":
                print("[Heartbeat] 无待办任务，跳过")
                return None
            print(f"[Heartbeat] 发现任务，执行中：{tasks}")
            result = await self.on_execute(tasks)
            if result and self.on_notify:
                await self.on_notify(result)
            return result
        except Exception as e:
            print(f"[Heartbeat] 执行失败：{e}")
            return None

    async def _decide(self, content: str) -> tuple[str, str]:
        """Phase 1：让 LLM 判断是否有待执行任务。"""
        messages = [
            {"role": "system", "content": "你是一个任务调度助手。审阅以下任务文件，判断是否有需要立即执行的任务。"},
            {"role": "user", "content": f"任务文件内容：\n\n{content}"},
        ]
        resp = await self._http.post(
            "/chat/completions",
            json={"model": QWEN_MODEL, "messages": messages,
                  "tools": _DECIDE_TOOL, "tool_choice": "required", "stream": False},
            headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
        )
        if not resp.is_success:
            raise RuntimeError(f"心跳决策 API 失败：{resp.status_code}")
        msg = resp.json()["choices"][0]["message"]
        calls = msg.get("tool_calls", [])
        if not calls:
            return "skip", ""
        import json
        args = json.loads(calls[0]["function"]["arguments"])
        return args.get("action", "skip"), args.get("tasks", "")

    def _read_file(self) -> str:
        if not _HEARTBEAT_FILE.exists():
            return ""
        content = _HEARTBEAT_FILE.read_text(encoding="utf-8")
        # 无实际任务（仅标题/注释）则跳过
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith(("#", "<!--"))]
        return content if lines else ""
