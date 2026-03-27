import json
import httpx
from . import tools as tool_registry
from . import builtin_tools  # noqa: F401 — 触发所有内置工具注册
from .prompt import ContextBuilder
from .config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL

_client = httpx.AsyncClient(
    base_url=QWEN_BASE_URL,
    timeout=120,
    trust_env=False,  # 禁用系统代理，避免代理超时干扰
)
_no_tool_models = {"qvq", "qwen-vl"}
_context = ContextBuilder()


async def _chat(messages: list[dict], profile: str = "full") -> dict:
    supports_tools = not any(m in QWEN_MODEL for m in _no_tool_models)
    schemas = tool_registry.get_schemas(profile)
    payload = {"model": QWEN_MODEL, "messages": messages, "stream": False}
    if schemas and supports_tools:
        payload["tools"] = schemas
    resp = await _client.post(
        "/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
    )
    if not resp.is_success:
        raise httpx.HTTPStatusError(
            f"{resp.status_code}: {resp.text}", request=resp.request, response=resp
        )
    return resp.json()["choices"][0]["message"]


async def _chat_simple(messages: list[dict]) -> dict:
    """无工具的纯文本 LLM 调用，供记忆整理/压缩使用。"""
    payload = {"model": QWEN_MODEL, "messages": messages, "stream": False}
    resp = await _client.post(
        "/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
    )
    if not resp.is_success:
        return {"content": ""}
    return resp.json()["choices"][0]["message"]


async def run(user_input: str, history: list[dict] | None = None,
              profile: str = "full") -> str:
    """运行 agent 循环，返回最终文本回复。"""
    system_prompt = _context.build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    for _ in range(10):
        msg = await _chat(messages, profile)
        messages.append(msg)
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return msg.get("content") or ""
        for tc in tool_calls:
            fn = tc["function"]
            result = await tool_registry.acall(fn["name"], fn["arguments"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    return "[已达最大迭代次数]"
