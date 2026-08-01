"""Tool Registry — a read-only capability catalog (能力清单).

The factory does NOT create tools. It only *selects* from capabilities that already
exist in the project (the compiler matches verbs → capabilities; the assembler binds
the enabled ones to real tool functions).

This module is intentionally a pure metadata catalog: it must NOT import the heavy
tool implementations (langchain / langgraph / rag). Binding to the real callables
happens later in the assembler.

The blog's "三板斧" is search / rag / bash. bash (shell execution) is registered so
it is discoverable, but marked risk="high" and defaults to disabled — it must be
explicitly enabled and human-approved before it can ever be bound at runtime.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Risk = Literal["low", "high"]


class ToolCapability(BaseModel):
    """One capability the compiler can pick and the assembler can bind."""

    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)
    verbs: list[str] = Field(default_factory=list)
    risk: Risk = "low"


# The catalog. Verbs include both Chinese and English triggers so the compiler can
# map plain-language actions ("查天气", "set a reminder") to capabilities.
_CAPABILITIES: list[ToolCapability] = [
    ToolCapability(
        name="weather",
        description="查询某个城市的当前天气（温度、天气、风力、湿度、穿衣/出行建议）。",
        input_schema={"city": "城市名或 AD 编码，例：'北京'、'Beijing'、'110000'"},
        verbs=["天气", "气温", "下雨", "weather", "temperature", "forecast"],
        risk="low",
    ),
    ToolCapability(
        name="rag_search",
        description="在长期记忆/知识库里做语义检索，取回与问题相关的资料片段（RAG）。",
        input_schema={"query": "检索问题", "top_k": "返回片段数，默认 3"},
        verbs=["知识库", "检索", "资料", "search", "rag", "retrieve", "查资料"],
        risk="low",
    ),
    ToolCapability(
        name="note",
        description="保存、搜索、列出用户的笔记。",
        input_schema={
            "content": "笔记内容",
            "query": "搜索关键词",
            "title": "可选标题",
        },
        verbs=["笔记", "记录", "记下", "note", "memo"],
        risk="low",
    ),
    ToolCapability(
        name="task",
        description="创建、列出、完成待办任务；用于把要做的事排进清单。",
        input_schema={
            "title": "任务标题",
            "priority": "low/medium/high/urgent",
            "due_date": "截止时间",
        },
        verbs=["任务", "待办", "安排", "排期", "日程", "task", "todo", "schedule"],
        risk="low",
    ),
    ToolCapability(
        name="reminder",
        description="设置、列出、延后提醒；到点通知用户。",
        input_schema={
            "title": "提醒标题",
            "remind_at": "提醒时间 YYYY-MM-DD HH:MM 或相对时间",
        },
        verbs=["提醒", "闹钟", "通知", "remind", "reminder", "alert"],
        risk="low",
    ),
    ToolCapability(
        name="calculator",
        description="计算数学表达式（四则运算、sqrt/sin/cos/log、pi/e 常量）。",
        input_schema={"expression": "数学表达式，例：'2 + 2'、'sqrt(16)'"},
        verbs=["计算", "算", "calculate", "math", "compute"],
        risk="low",
    ),
    ToolCapability(
        name="datetime",
        description="获取当前日期与时间（可指定时区、格式）。",
        input_schema={
            "timezone": "时区名，例：'Asia/Shanghai'",
            "format": "可选格式串",
        },
        verbs=["时间", "日期", "几点", "星期", "datetime", "now", "date", "time"],
        risk="low",
    ),
    ToolCapability(
        name="bash",
        description="在系统上执行 shell 命令（三板斧之一）。高危：可读写文件、访问网络。",
        input_schema={"command": "要执行的 shell 命令"},
        verbs=["执行", "运行命令", "shell", "bash", "command", "terminal"],
        risk="high",
    ),
]

_BY_NAME: dict[str, ToolCapability] = {c.name: c for c in _CAPABILITIES}


def list_capabilities() -> list[ToolCapability]:
    """All registered capabilities."""
    return list(_CAPABILITIES)


def get_capability(name: str) -> Optional[ToolCapability]:
    """Look up a capability by exact name, or None."""
    return _BY_NAME.get(name)


def find_by_verb(verb: str) -> list[ToolCapability]:
    """Capabilities whose verb list matches ``verb`` (case-insensitive substring)."""
    needle = verb.strip().lower()
    if not needle:
        return []
    matches: list[ToolCapability] = []
    for cap in _CAPABILITIES:
        for v in cap.verbs:
            vl = v.lower()
            if needle in vl or vl in needle:
                matches.append(cap)
                break
    return matches


def default_enabled(name: str) -> bool:
    """Whether a capability should be enabled by default.

    High-risk capabilities (e.g. bash) default to disabled — they require explicit
    opt-in plus human approval before the assembler will bind them.
    """
    cap = _BY_NAME.get(name)
    if cap is None:
        return False
    return cap.risk != "high"
