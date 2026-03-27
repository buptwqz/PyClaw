"""Cron 工具 — LLM 可调用的定时任务管理。"""
from ..tools import tool
from .. import cron as cron_service


@tool(
    description="添加定时任务。模式：reminder=直接提醒，task=让AI执行后通知。",
    section="runtime",
    profiles=["messaging", "full"],
)
def cron_add(
    message: str,
    mode: str = "reminder",
    every_seconds: int = 0,
    at: str = "",
    cron_expr: str = "",
) -> str:
    """
    message: 提醒内容或任务描述
    mode: reminder（直接提醒）或 task（AI执行）
    every_seconds: 每隔多少秒执行，0表示不用
    at: 指定执行时间（ISO格式，如 2025-01-01T09:00:00），留空不用
    cron_expr: cron表达式（如 '0 9 * * *' 表示每天9点），留空不用
    """
    return cron_service.add_job(
        message=message,
        every_seconds=every_seconds if every_seconds else None,
        at=at if at else None,
        cron_expr=cron_expr if cron_expr else None,
        mode=mode,
    )


@tool(description="列出所有定时任务。", section="runtime", profiles=["messaging", "full"])
def cron_list() -> str:
    return cron_service.list_jobs()


@tool(description="删除定时任务。", section="runtime", profiles=["messaging", "full"])
def cron_remove(job_id: str) -> str:
    """
    job_id: 任务ID（用 cron_list 查看）
    """
    return cron_service.remove_job(job_id)
