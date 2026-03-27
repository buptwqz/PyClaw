"""工具注册表

- @tool(description, section, profiles) 装饰器注册工具
- section: 工具分区（fs/web/memory/runtime/messaging）
- profiles: 适用场景列表（minimal/coding/messaging/full）
- 支持同步和异步工具
"""
import json
import inspect
from typing import Any, Callable

# profile 包含的 section
_PROFILE_SECTIONS: dict[str, set[str]] = {
    "minimal":   {"memory"},
    "coding":    {"fs", "runtime", "web", "memory"},
    "messaging": {"web", "memory", "messaging"},
    "full":      {"fs", "runtime", "web", "memory", "messaging"},
}

_registry: dict[str, dict] = {}


def tool(func: Callable | None = None, *, description: str | None = None,
         section: str = "memory", profiles: list[str] | None = None) -> Any:
    """装饰器：注册函数为 agent 可调用工具。

    支持：@tool 或 @tool(description='...', section='web', profiles=['full'])
    """
    _profiles = profiles or ["full"]

    def _register(fn: Callable) -> Callable:
        params = {}
        required = []
        sig = inspect.signature(fn)
        hints = fn.__annotations__
        for name, param in sig.parameters.items():
            if name == "return":
                continue
            py_type = hints.get(name, str)
            json_type = {str: "string", int: "integer", float: "number", bool: "boolean"}.get(py_type, "string")
            pdesc = ""
            if fn.__doc__:
                for line in fn.__doc__.splitlines():
                    line = line.strip()
                    if line.startswith(f"{name}:"):
                        pdesc = line.split(":", 1)[1].strip()
            params[name] = {"type": json_type, "description": pdesc}
            if param.default is inspect.Parameter.empty:
                required.append(name)
        _registry[fn.__name__] = {
            "func": fn,
            "section": section,
            "profiles": _profiles,
            "schema": {
                "type": "function",
                "function": {
                    "name": fn.__name__,
                    "description": description or (fn.__doc__ or "").strip().splitlines()[0],
                    "parameters": {
                        "type": "object",
                        "properties": params,
                        "required": required,
                    },
                },
            },
        }
        return fn

    if func is not None:
        return _register(func)
    return _register


def get_schemas(profile: str = "full") -> list[dict]:
    """返回指定 profile 下的工具 schema 列表。"""
    allowed = _PROFILE_SECTIONS.get(profile, set())
    return [
        v["schema"] for v in _registry.values()
        if v["section"] in allowed or profile == "full"
    ]


async def acall(name: str, args: str | dict) -> str:
    """异步调用工具（自动处理同步/异步）。"""
    if name not in _registry:
        return f"[错误] 未知工具：{name}"
    kwargs = json.loads(args) if isinstance(args, str) else args
    try:
        fn = _registry[name]["func"]
        if inspect.iscoroutinefunction(fn):
            return str(await fn(**kwargs))
        return str(fn(**kwargs))
    except Exception as e:
        return f"[错误] {e}"
