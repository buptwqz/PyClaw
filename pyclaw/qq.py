"""QQ Official Bot adapter using qq-botpy SDK."""
import asyncio
import botpy
from botpy.message import Message, GroupMessage, C2CMessage
from . import core
from .config import QQ_APPID, QQ_SECRET, QQ_SANDBOX, HEARTBEAT_INTERVAL, ADMIN_OPENID
from .memory import load_session, save_session, log_history, auto_consolidate, compress_session
from .heartbeat import HeartbeatService
from . import cron as cron_service

# 短期记忆：当前进程内的会话缓存（重启后从持久化恢复）
_cache: dict[str, list[dict]] = {}


def _get_session(key: str) -> list[dict]:
    if key not in _cache:
        _cache[key] = load_session(key)  # 从持久化加载
    return _cache[key]


async def _handle(text: str, key: str, send_fn) -> None:
    history = _get_session(key)
    reply = await core.run(text, history)

    # 更新会话
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})

    # 写历史日志
    log_history("user", text)
    log_history("assistant", reply)

    # 发送回复
    await send_fn(reply)

    # 后台任务：持久化 + 压缩 + 长期记忆整理
    asyncio.create_task(_background(key, history, text, reply))


async def _background(key: str, history: list[dict], text: str, reply: str) -> None:
    # 压缩会话（超过阈值时）
    compressed = await compress_session(key, history, core._chat_simple)
    _cache[key] = compressed
    # 持久化会话
    save_session(key, compressed)
    # 提取长期记忆
    await auto_consolidate(text, reply, core._chat_simple)


class PyClaw(botpy.Client):
    async def on_ready(self) -> None:
        print(f"[PyClaw] Bot 已连接，准备就绪")

        # cron 通知回调
        async def _cron_notify(result: str) -> None:
            if ADMIN_OPENID:
                await self.api.post_c2c_message(
                    openid=ADMIN_OPENID, msg_type=0, content=result, msg_id="cron"
                )

        cron_service.start(notify_fn=_cron_notify, run_fn=core.run)

        if HEARTBEAT_INTERVAL > 0:
            async def _execute(task_desc: str) -> str:
                return await core.run(f"[心跳任务] {task_desc}")

            async def _notify(result: str) -> None:
                if ADMIN_OPENID:
                    await self.api.post_c2c_message(
                        openid=ADMIN_OPENID, msg_type=0, content=result, msg_id="heartbeat"
                    )

            self._heartbeat = HeartbeatService(
                on_execute=_execute,
                on_notify=_notify,
                interval_s=HEARTBEAT_INTERVAL,
            )
            self._heartbeat.start()
    async def on_at_message_create(self, message: Message) -> None:
        text = message.content.strip()
        for seg in (message.mentions or []):
            text = text.replace(f"<@!{seg.id}>", "").replace(f"<@{seg.id}>", "")
        text = text.strip()
        if not text:
            return
        key = f"guild_{message.channel_id}"
        await _handle(text, key, lambda r: message.reply(content=r))

    async def on_group_at_message_create(self, message: GroupMessage) -> None:
        text = message.content.strip()
        key = f"group_{message.group_openid}"
        await _handle(text, key, lambda r: self.api.post_group_message(
            group_openid=message.group_openid, msg_type=0, content=r, msg_id=message.id,
        ))

    async def on_c2c_message_create(self, message: C2CMessage) -> None:
        text = message.content.strip()
        key = f"c2c_{message.author.user_openid}"
        await _handle(text, key, lambda r: self.api.post_c2c_message(
            openid=message.author.user_openid, msg_type=0, content=r, msg_id=message.id,
        ))


def create_client() -> PyClaw:
    intents = botpy.Intents(
        public_guild_messages=True,
        public_messages=True,
    )
    return PyClaw(intents=intents, is_sandbox=QQ_SANDBOX)
