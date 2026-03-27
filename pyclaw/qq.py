"""QQ Official Bot adapter using qq-botpy SDK.

Handles:
- Guild channel messages (频道消息, @bot)
- Group messages (群聊, @bot)  — requires group bot permission
- C2C private messages (单聊)
"""
import asyncio
import botpy
from botpy.message import Message, GroupMessage, C2CMessage
from . import core
from .config import QQ_APPID, QQ_SECRET, QQ_SANDBOX
from .memory import log_history

# per-session history keyed by openid/channel_id
_history: dict[str, list[dict]] = {}


def _get_history(key: str) -> list[dict]:
    return _history.setdefault(key, [])


def _update_history(key: str, user_text: str, bot_reply: str) -> None:
    h = _history[key]
    h.append({"role": "user", "content": user_text})
    h.append({"role": "assistant", "content": bot_reply})
    if len(h) > 40:
        _history[key] = h[-40:]
    log_history("user", user_text)
    log_history("assistant", bot_reply)


class PyClaw(botpy.Client):
    # ── Guild channel (频道) ──────────────────────────────────────────────────
    async def on_at_message_create(self, message: Message) -> None:
        text = message.content.strip()
        # strip @bot mention prefix
        for seg in (message.mentions or []):
            text = text.replace(f"<@!{seg.id}>", "").replace(f"<@{seg.id}>", "")
        text = text.strip()
        if not text:
            return
        key = f"guild_{message.channel_id}"
        reply = await core.run(text, _get_history(key))
        _update_history(key, text, reply)
        await message.reply(content=reply)

    # ── Group (群聊) ──────────────────────────────────────────────────────────
    async def on_group_at_message_create(self, message: GroupMessage) -> None:
        text = message.content.strip()
        key = f"group_{message.group_openid}"
        reply = await core.run(text, _get_history(key))
        _update_history(key, text, reply)
        await self.api.post_group_message(
            group_openid=message.group_openid,
            msg_type=0,
            content=reply,
            msg_id=message.id,
        )

    # ── C2C private (单聊) ────────────────────────────────────────────────────
    async def on_c2c_message_create(self, message: C2CMessage) -> None:
        text = message.content.strip()
        key = f"c2c_{message.author.user_openid}"
        reply = await core.run(text, _get_history(key))
        _update_history(key, text, reply)
        await self.api.post_c2c_message(
            openid=message.author.user_openid,
            msg_type=0,
            content=reply,
            msg_id=message.id,
        )


def create_client() -> PyClaw:
    intents = botpy.Intents(
        public_guild_messages=True,   # 频道 @消息
        public_messages=True,         # 群/C2C 消息（需申请权限）
    )
    return PyClaw(intents=intents, is_sandbox=QQ_SANDBOX)
