import json
import inspect
from typing import Any, Callable

_registry: dict[str, dict] = {}


def tool(func: Callable) -> Callable:
    """Decorator to register a function as an agent tool."""
    params = {}
    required = []
    sig = inspect.signature(func)
    hints = func.__annotations__

    for name, param in sig.parameters.items():
        if name == "return":
            continue
        py_type = hints.get(name, str)
        json_type = {str: "string", int: "integer", float: "number", bool: "boolean"}.get(py_type, "string")
        desc = ""
        # parse description from docstring "name: description" lines
        if func.__doc__:
            for line in func.__doc__.splitlines():
                line = line.strip()
                if line.startswith(f"{name}:"):
                    desc = line.split(":", 1)[1].strip()
        params[name] = {"type": json_type, "description": desc}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    _registry[func.__name__] = {
        "func": func,
        "schema": {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": (func.__doc__ or "").strip().splitlines()[0] if func.__doc__ else "",
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": required,
                },
            },
        },
    }
    return func


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
