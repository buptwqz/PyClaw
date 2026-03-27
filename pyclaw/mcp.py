"""MCP (Model Context Protocol) 客户端

支持两种传输方式：
- stdio：本地进程，通过标准输入输出通信
- sse/streamable_http：远程服务器，通过 HTTP POST + SSE 通信

MCP server 配置在 mcp_servers.json 中声明。
"""
import json
import asyncio
import httpx
from pathlib import Path
from typing import Any
from . import tools as tool_registry

_MCP_CONFIG = Path.cwd() / "mcp_servers.json"
_clients: dict[str, Any] = {}


# ── Schema 规范化（参考 nanobot）─────────────────────────────────────────────

def _extract_nullable_branch(options: Any) -> tuple[dict, bool] | None:
    """提取 oneOf/anyOf 中的非 null 分支（用于 nullable union）。"""
    if not isinstance(options, list):
        return None
    non_null = [o for o in options if isinstance(o, dict) and o.get("type") != "null"]
    saw_null = any(isinstance(o, dict) and o.get("type") == "null" for o in options)
    if saw_null and len(non_null) == 1:
        return non_null[0], True
    return None


def _normalize_schema(schema: Any) -> dict:
    """将 MCP 返回的 JSON Schema 规范化为 OpenAI/Qwen 兼容格式。"""
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}

    s = dict(schema)

    # 处理 type: ["string", "null"] → type: "string", nullable: true
    raw_type = s.get("type")
    if isinstance(raw_type, list):
        non_null = [t for t in raw_type if t != "null"]
        if "null" in raw_type and len(non_null) == 1:
            s["type"] = non_null[0]
            s["nullable"] = True

    # 处理 oneOf/anyOf nullable union
    for key in ("oneOf", "anyOf"):
        result = _extract_nullable_branch(s.get(key))
        if result is not None:
            branch, _ = result
            merged = {k: v for k, v in s.items() if k != key}
            merged.update(branch)
            merged["nullable"] = True
            s = merged
            break

    # 递归规范化 properties
    if "properties" in s and isinstance(s["properties"], dict):
        s["properties"] = {k: _normalize_schema(v) for k, v in s["properties"].items()}

    # 递归规范化 items（array）
    if "items" in s:
        s["items"] = _normalize_schema(s["items"])

    return s



class MCPSSEClient:
    """通过 SSE 连接远程 MCP server（Streamable HTTP / SSE transport）。"""

    def __init__(self, name: str, url: str, headers: dict | None = None):
        self.name = name
        self.url = url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **(headers or {}),
        }
        self._http = httpx.AsyncClient(timeout=30, trust_env=False)
        self._session_id: str | None = None

    async def start(self) -> None:
        """初始化握手，获取 session_id。"""
        resp = await self._http.post(
            self.url,
            json={"jsonrpc": "2.0", "id": 0, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05",
                             "capabilities": {},
                             "clientInfo": {"name": "pyclaw", "version": "1.0"}}},
            headers=self._headers,
        )
        resp.raise_for_status()
        self._session_id = resp.headers.get("mcp-session-id")
        # 必须发送 initialized 通知，否则部分 server 不响应后续请求
        notify_headers = {**self._headers}
        if self._session_id:
            notify_headers["mcp-session-id"] = self._session_id
        await self._http.post(
            self.url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=notify_headers,
        )

    async def list_tools(self) -> list[dict]:
        headers = {**self._headers}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        resp = await self._http.post(
            self.url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json().get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        headers = {**self._headers}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        resp = await self._http.post(
            self.url,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": tool_name, "arguments": arguments}},
            headers=headers,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        content = result.get("content", [])
        return "\n".join(c.get("text", "") for c in content if c.get("type") == "text")

    async def stop(self) -> None:
        await self._http.aclose()

class MCPClient:
    """简化版 MCP stdio 客户端。"""

    def __init__(self, name: str, command: list[str], env: dict | None = None):
        self.name = name
        self.command = command
        self.env = env or {}
        self._proc: asyncio.subprocess.Process | None = None
        self._req_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None

    async def start(self) -> None:
        import os
        merged_env = {**os.environ, **self.env}
        self._proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=merged_env,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        # 初始化握手
        await self._send({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                          "params": {"protocolVersion": "2024-11-05",
                                     "capabilities": {},
                                     "clientInfo": {"name": "pyclaw", "version": "1.0"}}})

    async def _read_loop(self) -> None:
        while self._proc and not self._proc.stdout.at_eof():  # type: ignore
            line = await self._proc.stdout.readline()  # type: ignore
            if not line:
                break
            try:
                msg = json.loads(line)
                rid = msg.get("id")
                if rid in self._pending:
                    self._pending[rid].set_result(msg)
            except Exception:
                pass

    async def _send(self, payload: dict) -> dict:
        rid = payload["id"]
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = fut
        data = json.dumps(payload).encode() + b"\n"
        self._proc.stdin.write(data)  # type: ignore
        await self._proc.stdin.drain()  # type: ignore
        try:
            return await asyncio.wait_for(fut, timeout=10)
        finally:
            self._pending.pop(rid, None)

    async def list_tools(self) -> list[dict]:
        self._req_id += 1
        resp = await self._send({"jsonrpc": "2.0", "id": self._req_id,
                                  "method": "tools/list", "params": {}})
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> str:
        self._req_id += 1
        resp = await self._send({"jsonrpc": "2.0", "id": self._req_id,
                                  "method": "tools/call",
                                  "params": {"name": name, "arguments": arguments}})
        content = resp.get("result", {}).get("content", [])
        return "\n".join(c.get("text", "") for c in content if c.get("type") == "text")

    async def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            await self._proc.wait()


_clients: dict[str, MCPClient | MCPSSEClient] = {}


async def load_mcp_servers() -> None:
    """加载 mcp_servers.json，支持两种格式：
    - { "servers": [{"name", "transport", "url", ...}] }  (PyClaw 格式)
    - { "mcpServers": {"name": {"type", "url", ...}} }    (标准 MCP 格式)
    """
    if not _MCP_CONFIG.exists():
        return
    config = json.loads(_MCP_CONFIG.read_text(encoding="utf-8"))

    # 统一转为 list[dict]
    entries: list[dict] = []
    if "mcpServers" in config:
        for name, cfg in config["mcpServers"].items():
            entries.append({"name": name, **cfg})
    else:
        entries = config.get("servers", [])

    for entry in entries:
        name = entry["name"]
        transport = entry.get("transport", entry.get("type", "stdio"))
        try:
            if transport in ("sse", "streamable_http"):
                client: MCPClient | MCPSSEClient = MCPSSEClient(
                    name=name, url=entry["url"], headers=entry.get("headers")
                )
            else:
                client = MCPClient(
                    name=name, command=entry["command"], env=entry.get("env", {})
                )
            await client.start()
            tools = await client.list_tools()
            print(f"[MCP] {name} 返回工具：{[t['name'] for t in tools]}")
            for t in tools:
                _register_mcp_tool(client, t)
            _clients[name] = client
            print(f"[MCP] 已加载 {name}（{transport}）：{len(tools)} 个工具")
        except Exception as e:
            print(f"[MCP] 加载 {name} 失败：{e}")


def _register_mcp_tool(client: Any, tool_def: dict) -> None:
    """将 MCP 工具包装为 pyclaw 工具并注册。"""
    tool_name = f"{client.name}__{tool_def['name']}"
    description = tool_def.get("description", "")
    # 规范化 schema，确保 Qwen API 可识别
    raw_schema = tool_def.get("inputSchema", {"type": "object", "properties": {}})
    input_schema = _normalize_schema(raw_schema)

    async def _mcp_call(**kwargs) -> str:
        return await client.call_tool(tool_def["name"], kwargs)

    _mcp_call.__name__ = tool_name
    _mcp_call.__doc__ = description

    tool_registry._registry[tool_name] = {
        "func": _mcp_call,
        "section": "mcp",
        "profiles": ["full"],
        "schema": {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": input_schema,
            },
        },
    }


async def stop_all() -> None:
    for client in _clients.values():
        await client.stop()
