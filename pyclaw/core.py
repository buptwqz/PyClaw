import json
import httpx
from . import tools as tool_registry
from .prompt import ContextBuilder
from .config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL

_client = httpx.AsyncClient(base_url=QWEN_BASE_URL, timeout=60)
_no_tool_models = {"qvq", "qwen-vl"}
_context = ContextBuilder()


async def _chat(messages: list[dict]) -> dict:
    supports_tools = not any(m in QWEN_MODEL for m in _no_tool_models)
    schemas = tool_registry.get_schemas()
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


async def run(
    user_input: str,
    history: list[dict] | None = None,
    *,
    extra_skills: list[str] | None = None,
) -> str:
    """Run the agent loop.

    System prompt is built from SOUL.md + AGENTS.md + always-skills +
    any extra_skills passed in.
    """
    system_prompt = _context.build_system_prompt(extra_skill_names=extra_skills)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    for _ in range(10):
        msg = await _chat(messages)
        messages.append(msg)
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return msg.get("content") or ""
        for tc in tool_calls:
            fn = tc["function"]
            result = tool_registry.call(fn["name"], fn["arguments"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    return "[max iterations reached]"
