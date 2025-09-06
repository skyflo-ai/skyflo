import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from litellm import acompletion

from ..config import settings
from ..models.conversation import Conversation
from ..agent.prompts import CHAT_TITLE_PROMPT
from ..utils.helpers import get_api_key_for_provider
from ..services.conversation_persistence import ConversationPersistenceService


logger = logging.getLogger(__name__)


class TitleDecision(BaseModel):
    title: str = Field(..., min_length=1, max_length=60)


def _clean_text_for_title(text: str) -> str:
    cleaned = re.sub(r"[\n\r\t]", " ", text or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r'[\.!?,;:"\'`]+', "", cleaned)
    return cleaned.strip()


async def generate_chat_title(
    messages: List[Dict[str, Any]], model: str, api_key: Optional[str] = None
) -> str:
    curated = messages[-6:] if len(messages) > 6 else messages
    judge_messages = curated + [{"role": "user", "content": CHAT_TITLE_PROMPT}]

    completion_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": judge_messages,
        "response_format": TitleDecision,
        "temperature": 0.2,
        "max_tokens": 64,
    }
    if api_key:
        completion_kwargs["api_key"] = api_key
    if getattr(settings, "LLM_HOST", None):
        completion_kwargs["api_base"] = settings.LLM_HOST

    try:
        resp = await acompletion(**completion_kwargs)
        parsed = TitleDecision.model_validate_json(resp.choices[0].message.content)
        return _clean_text_for_title(parsed.title)
    except Exception:
        fallback = ""
        for msg in reversed(curated):
            if isinstance(msg, dict) and msg.get("role") == "user":
                fallback = str(msg.get("content", ""))
                break
        if not fallback:
            return "New Conversation"
        cleaned = _clean_text_for_title(fallback)
        words = cleaned.split()
        return " ".join(words[:6]) or "New Conversation"


async def generate_and_store_title(
    conversation_id: str,
    persistence: ConversationPersistenceService,
) -> None:
    try:
        model = settings.LLM_MODEL
        provider = model.split("/")[0] if "/" in model else "openai"
        api_key: Optional[str] = get_api_key_for_provider(provider)

        llm_messages: List[Dict[str, Any]] = []
        assistant_seen = False

        for _ in range(16):
            conversation = await Conversation.get(id=conversation_id)
            if conversation.title:
                return
            try:
                llm_messages = await persistence.build_llm_messages_for_title_generation(
                    conversation
                )
            except Exception:
                llm_messages = []

            if any(
                isinstance(m, dict)
                and m.get("role") == "assistant"
                and str(m.get("content", "")).strip()
                for m in llm_messages
            ):
                assistant_seen = True
                break

            await asyncio.sleep(0.5)  # ~8 seconds at 0.5s intervals

        if not assistant_seen:
            # Fallback to the most recent user message only
            latest_user: Optional[Dict[str, Any]] = None
            for m in reversed(llm_messages):
                if isinstance(m, dict) and m.get("role") == "user":
                    latest_user = m
                    break
            llm_messages = [latest_user] if latest_user else []

        title = await generate_chat_title(llm_messages, model, api_key)
        title = _clean_text_for_title(title)[:60]
        if not title:
            return

        await persistence.set_title(conversation_id, title)
    except Exception as e:
        logger.error(f"Error in generate_and_store_title for {conversation_id}: {e}")
