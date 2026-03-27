"""Entry point — register tools here, then run the QQ official bot."""
from pyclaw import tool, create_client
from pyclaw.config import QQ_APPID, QQ_SECRET


# ── Example tools ─────────────────────────────────────────────────────────────

@tool(description="Get the current time in ISO format.")
def get_time() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


@tool(description="Evaluate a simple math expression safely.")
def calculate(expression: str) -> str:
    """expression: a Python-style math expression, e.g. '2 + 3 * 4'"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# ── Start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not QQ_APPID or not QQ_SECRET:
        raise SystemExit("[error] QQ_APPID and QQ_SECRET must be set in .env")
    print(f"PyClaw starting (appid={QQ_APPID[:6]}...)")
    client = create_client()
    client.run(appid=QQ_APPID, secret=QQ_SECRET)
