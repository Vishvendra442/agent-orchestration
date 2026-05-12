from typing import Any
from langchain_core.tools import tool as lc_tool

_REGISTRY: dict[str, Any] = {}


def register_tool(name: str, func):
    _REGISTRY[name] = func


def get_tool(name: str):
    if name not in _REGISTRY:
        raise KeyError(f"Tool '{name}' not found. Available: {list(_REGISTRY.keys())}")
    return _REGISTRY[name]


def get_tools(names: list[str]) -> list:
    return [get_tool(n) for n in names]


def list_tool_names() -> list[str]:
    return list(_REGISTRY.keys())


def _bootstrap():
    from app.runtime.tools import web_search, calculator, code_executor, summarizer  # noqa: F401


_bootstrap()
