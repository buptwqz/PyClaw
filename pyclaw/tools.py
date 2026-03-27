import json
import inspect
from typing import Any, Callable

_registry: dict[str, dict] = {}


def tool(func: Callable | None = None, *, description: str | None = None) -> Any:
    """Decorator to register a function as an agent tool.
    Supports both @tool and @tool(description='...') usage.
    """
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

        tool_desc = description or ((fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else "")
        _registry[fn.__name__] = {
            "func": fn,
            "schema": {
                "type": "function",
                "function": {
                    "name": fn.__name__,
                    "description": tool_desc,
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


def get_schemas() -> list[dict]:
    return [v["schema"] for v in _registry.values()]


def call(name: str, args: str | dict) -> Any:
    if name not in _registry:
        return f"[error] unknown tool: {name}"
    kwargs = json.loads(args) if isinstance(args, str) else args
    try:
        return _registry[name]["func"](**kwargs)
    except Exception as e:
        return f"[error] {e}"
