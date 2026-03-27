"""定时任务服务

支持三种调度模式：
- at: 指定时刻执行一次（ISO datetime）
- every: 每隔 N 秒执行
- cron: cron 表达式（需安装 croniter）

任务持久化到 memory/cron.json。
"""
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable

_CRON_FILE = Path.cwd() / "memory" / "cron.json"


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _load() -> list[dict]:
    if _CRON_FILE.exists():
        try:
            return json.loads(_CRON_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(jobs: list[dict]) -> None:
    _CRON_FILE.parent.mkdir(exist_ok=True)
    _CRON_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 公开 API（供 builtin_tools/cron.py 调用）────────────────────────────────

def add_job(message: str, every_seconds: int | None = None,
            at: str | None = None, cron_expr: str | None = None,
            mode: str = "task") -> str:
    """添加定时任务。"""
    jobs = _load()
    job_id = str(int(_now_ts() * 1000))[-6:]  # 6位短ID

    if at:
        job = {"id": job_id, "kind": "at", "at": at,
               "message": message, "mode": mode, "done": False}
    elif cron_expr:
        job = {"id": job_id, "kind": "cron", "expr": cron_expr,
               "message": message, "mode": mode, "next_run": _now_ts()}
    elif every_seconds:
        job = {"id": job_id, "kind": "every", "seconds": every_seconds,
               "message": message, "mode": mode, "next_run": _now_ts() + every_seconds}
    else:
        return "错误：必须指定 at、every_seconds 或 cron_expr 之一"

    jobs.append(job)
    _save(jobs)
    return f"已添加定时任务 [{job_id}]：{message}"


def list_jobs() -> str:
    """列出所有定时任务。"""
    jobs = _load()
    if not jobs:
        return "暂无定时任务"
    lines = []
    for j in jobs:
        if j["kind"] == "at":
            schedule = f"在 {j['at']}"
        elif j["kind"] == "every":
            schedule = f"每 {j['seconds']} 秒"
        else:
            schedule = f"cron: {j['expr']}"
        lines.append(f"[{j['id']}] {schedule} → {j['message']} (模式: {j['mode']})")
    return "\n".join(lines)


def remove_job(job_id: str) -> str:
    """删除定时任务。"""
    jobs = _load()
    before = len(jobs)
    jobs = [j for j in jobs if j["id"] != job_id]
    if len(jobs) == before:
        return f"未找到任务 [{job_id}]"
    _save(jobs)
    return f"已删除任务 [{job_id}]"


# ── 调度循环 ─────────────────────────────────────────────────────────────────

class CronService:
    def __init__(self, execute_fn: Callable[[str], Awaitable[str]],
                 notify_fn: Callable[[str], Awaitable[None]]):
        self._execute = execute_fn  # 执行任务（调用 agent loop）
        self._notify = notify_fn    # 通知用户（发 QQ 消息）
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(10)  # 每10秒检查一次
            now = _now_ts()
            jobs = _load()
            changed = False

            for job in jobs:
                if job.get("done"):
                    continue
                should_run = False

                if job["kind"] == "at":
                    try:
                        from datetime import datetime
                        run_at = datetime.fromisoformat(job["at"]).timestamp()
                        if now >= run_at:
                            should_run = True
                            job["done"] = True
                            changed = True
                    except Exception:
                        pass

                elif job["kind"] == "every":
                    if now >= job.get("next_run", 0):
                        should_run = True
                        job["next_run"] = now + job["seconds"]
                        changed = True

                elif job["kind"] == "cron":
                    try:
                        from croniter import croniter
                        ci = croniter(job["expr"])
                        next_t = ci.get_next(float)
                        if now >= job.get("next_run", 0):
                            should_run = True
                            job["next_run"] = next_t
                            changed = True
                    except Exception:
                        pass

                if should_run:
                    asyncio.create_task(self._run_job(job))

            if changed:
                _save([j for j in jobs if not (j.get("done") and j["kind"] == "at")])

    async def _run_job(self, job: dict) -> None:
        try:
            if job["mode"] == "reminder":
                await self._notify(job["message"])
            else:  # task mode: LLM 执行
                result = await self._execute(job["message"])
                await self._notify(f"[定时任务 {job['id']}]\n{result}")
        except Exception as e:
            await self._notify(f"[定时任务 {job['id']} 出错] {e}")


# ── 模块级接口 ────────────────────────────────────────────────────────────────

_service: CronService | None = None


def start(notify_fn, run_fn) -> None:
    """启动全局 cron 调度器。"""
    global _service
    _service = CronService(execute_fn=run_fn, notify_fn=notify_fn)
    _service.start()


def stop() -> None:
    if _service:
        _service.stop()
