"""
Philosophy Master agent: chat + streaming with preset-controlled style and safety boundaries.

Security notes:
- Treat all user inputs as untrusted.
- Do not provide instructions for self-harm, violence, or illegal activity.
- Avoid logging raw user content in production.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator

from app.core.config import settings
from app.schemas.philosophy import (
    PhilosophyChatRequest,
    PhilosophyChatResponse,
    PhilosophyPreset,
)
from app.services.llm.provider_factory import LLMProviderFactory

logger = logging.getLogger(__name__)


ALLOWED_SCHOOLS: set[str] = {
    "eastern",
    "western",
    "zen",
    "confucian",
    "stoic",
    "existential",
    "kant",
    "nietzsche",
    "schopenhauer",
    "idealism",
    "materialism",
    "mixed",
}
ALLOWED_TONES: set[str] = {"gentle", "direct", "rigorous", "zen"}
ALLOWED_DEPTHS: set[str] = {"shallow", "medium", "deep"}
ALLOWED_MODES: set[str] = {"advice", "story", "compare", "daily_practice"}


_SELF_HARM_PATTERNS = [
    re.compile(r"\bkill\s+myself\b", re.IGNORECASE),
    re.compile(r"\bsuicide\b", re.IGNORECASE),
    re.compile(r"自杀|轻生|想死|不想活了|结束生命"),
]

_VIOLENCE_PATTERNS = [
    re.compile(r"\bhow\s+to\s+kill\b", re.IGNORECASE),
    re.compile(r"杀人|爆炸|做炸弹|投毒|枪支|制枪"),
]


@dataclass(frozen=True)
class NormalizedPreset:
    school: str
    tone: str
    depth: str
    mode: str
    multi_perspective: bool


def _normalize_preset(preset: PhilosophyPreset | None) -> NormalizedPreset:
    school = (preset.school if preset else None) or "mixed"
    tone = (preset.tone if preset else None) or "gentle"
    depth = (preset.depth if preset else None) or "medium"
    mode = (preset.mode if preset else None) or "advice"
    multi_perspective = bool((preset.multi_perspective if preset else False))

    if school not in ALLOWED_SCHOOLS:
        raise ValueError(f"Invalid preset.school. Allowed: {sorted(ALLOWED_SCHOOLS)}")
    if tone not in ALLOWED_TONES:
        raise ValueError(f"Invalid preset.tone. Allowed: {sorted(ALLOWED_TONES)}")
    if depth not in ALLOWED_DEPTHS:
        raise ValueError(f"Invalid preset.depth. Allowed: {sorted(ALLOWED_DEPTHS)}")
    if mode not in ALLOWED_MODES:
        raise ValueError(f"Invalid preset.mode. Allowed: {sorted(ALLOWED_MODES)}")

    if mode == "compare":
        multi_perspective = True

    return NormalizedPreset(
        school=school,
        tone=tone,
        depth=depth,
        mode=mode,
        multi_perspective=multi_perspective,
    )


def _is_crisis_or_disallowed(message: str) -> bool:
    text = message or ""
    for p in _SELF_HARM_PATTERNS + _VIOLENCE_PATTERNS:
        if p.search(text):
            return True
    return False


def _safe_refusal_message() -> str:
    return (
        "我听到你在表达非常强烈的痛苦或危险念头。出于安全原因，我不能提供任何自伤、伤害他人或违法行为的具体方法。\n\n"
        "如果你正处在可能伤害自己/他人的风险中，请优先：\n"
        "- 立即联系当地紧急服务（如 110/120）或当地危机干预热线\n"
        "- 联系你信任的人（家人/朋友/同事）陪你一起度过此刻\n"
        "- 若你已在接受心理/精神科帮助，也可以尽快联系你的医生或治疗师\n\n"
        "如果你愿意，你也可以告诉我：你现在最难受的点是什么、事情发生了什么、你最担心的后果是什么？"
        "我可以在不涉及危险细节的前提下，陪你一起梳理与寻找更安全的下一步。"
    )


def _system_instructions() -> str:
    return (
        "你是一位哲学大师（Philosophy Master），精通东西方哲学思想（禅宗/佛教、儒家、斯多葛、存在主义、"
        "康德、尼采、叔本华、唯心/唯物等）。\n"
        "你的任务是帮助用户从哲学角度澄清问题、辨析价值与选择，并给出可执行的建议与练习。\n"
        "你不是心理治疗师/医生/律师，不做诊断，不提供危害自己或他人的方法，不提供违法指导。\n"
        "输出要求：用中文回答，结构清晰，尽量用 markdown 标题/列表。\n"
    )


def _preset_instructions(p: NormalizedPreset) -> str:
    pieces: list[str] = []
    pieces.append(
        f"风格预设：school={p.school}, tone={p.tone}, depth={p.depth}, mode={p.mode}, multi_perspective={p.multi_perspective}"
    )

    if p.mode == "advice":
        pieces.append("请按以下结构输出：\n## 哲学视角\n## 可执行建议\n## 反思问题")
    elif p.mode == "compare":
        pieces.append(
            "请用 2-3 个不同哲学流派对同一问题进行对照分析，并给出每种视角的优势/局限与建议。"
        )
    elif p.mode == "story":
        pieces.append(
            "请讲一个简短的哲学故事/寓言/典故，然后明确写出它对应到用户处境的启示与行动建议。"
        )
    elif p.mode == "daily_practice":
        pieces.append(
            "请提供：一句原则/箴言 + 一个小练习（可在今天完成）+ 1-3 个反思问题。"
        )

    if p.multi_perspective and p.mode != "compare":
        pieces.append("额外要求：再补充 1-2 个不同流派的简短补充视角，并指出差异。")

    if p.depth == "shallow":
        pieces.append("深度要求：简洁、可读、建议更具体，避免长篇论证。")
    elif p.depth == "deep":
        pieces.append("深度要求：可以稍微深入论证，但仍要落到行动建议与反思问题。")

    if p.tone == "zen":
        pieces.append("语气要求：简练、点拨式、留白，但不要模糊到无法执行。")
    elif p.tone == "rigorous":
        pieces.append("语气要求：逻辑清晰，概念定义明确，尽量减少空泛。")
    elif p.tone == "direct":
        pieces.append("语气要求：直截了当但保持尊重与同理。")
    else:
        pieces.append("语气要求：温和、同理、不过度安慰，强调自我选择与行动。")

    return "\n".join(pieces)


def _build_prompt(message: str, context: str | None, preset: NormalizedPreset) -> str:
    ctx = (context or "").strip()
    return (
        f"{_system_instructions()}\n"
        f"{_preset_instructions(preset)}\n\n"
        "用户问题：\n"
        f"{message.strip()}\n\n"
        + (f"补充背景（可选）：\n{ctx}\n\n" if ctx else "")
        + "请开始回答："
    )


class PhilosophyMasterService:
    def __init__(self) -> None:
        self._provider = LLMProviderFactory.get_provider(
            provider_type=getattr(settings, "LLM_PROVIDER", "openai"),
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            verify_ssl=getattr(settings, "LLM_VERIFY_SSL", True),
            timeout=int(getattr(settings, "LLM_TIMEOUT", 30)),
        )

    async def chat(self, req: PhilosophyChatRequest) -> PhilosophyChatResponse:
        preset = _normalize_preset(req.preset)
        if _is_crisis_or_disallowed(req.message):
            return PhilosophyChatResponse(
                content=_safe_refusal_message(), sections=None
            )

        prompt = _build_prompt(req.message, req.context, preset)
        chunks: list[str] = []
        async for token in self._provider.generate_completion_stream(
            prompt, temperature=0.5, max_tokens=2048
        ):
            chunks.append(token)
        content = "".join(chunks).strip()
        return PhilosophyChatResponse(content=content, sections=None)

    async def chat_stream(
        self, req: PhilosophyChatRequest
    ) -> AsyncIterator[dict[str, Any]]:
        preset = _normalize_preset(req.preset)
        yield {
            "type": "meta",
            "preset": json.loads(json.dumps(preset.__dict__)),
        }  # JSON-safe

        if _is_crisis_or_disallowed(req.message):
            safe = _safe_refusal_message()
            # small chunking to emulate streaming
            for i in range(0, len(safe), 24):
                yield {"type": "token", "content": safe[i : i + 24]}
            yield {"type": "done"}
            return

        prompt = _build_prompt(req.message, req.context, preset)
        try:
            async for token in self._provider.generate_completion_stream(
                prompt, temperature=0.5, max_tokens=2048
            ):
                yield {"type": "token", "content": token}
            yield {"type": "done"}
        except Exception as e:
            logger.exception("Philosophy streaming failed: %s", e)
            yield {
                "type": "error",
                "content": "Philosophy Master failed. Please try again.",
            }
