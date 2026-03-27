import json
import httpx
from . import tools as tool_registry
from .config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL, SYSTEM_PROMPT

_client = httpx.AsyncClient(base_url=QWEN_BASE_URL, timeout=60)


async def _chat(messages: list[dict]) -> dict:
    schemas = tool_registry.get_schemas()
    payload = {
        "model": QWEN_MODEL,
        "messages": messages,
        "stream": False,
    }
    if schemas:
        payload["tools"] = schemas
    resp = await _client.post(
        "/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


async def run(user_input: str, history: list[dict] | None = None) -> str:
    """Run the agent loop and return the final text response."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    for _ in range(10):  # max iterations
        msg = await _chat(messages)
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return msg.get("content") or ""

        # execute all tool calls
        for tc in tool_calls:
            fn = tc["function"]
            result = tool_registry.call(fn["name"], fn["arguments"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    return "[max iterations reached]"
