"""Robust LLM helper for PeerLens agents."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_env() -> None:
    """Reload environment variables so changes in .env take effect immediately."""
    load_dotenv(os.path.join(_backend_dir, ".env"), override=True)
    load_dotenv(os.path.join(os.path.dirname(_backend_dir), ".env"), override=True)
    load_dotenv(override=True)


_load_env()

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = Any

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

T = TypeVar("T", bound=BaseModel)


def get_default_llm(model_name: Optional[str] = None, temperature: float = 0.1) -> BaseChatModel:
    """Return configured ChatGoogleGenerativeAI or ChatOpenAI instance using .env settings."""
    _load_env()
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest"
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    if gemini_key and ChatGoogleGenerativeAI:
        target_model = model_name or gemini_model
        return ChatGoogleGenerativeAI(
            model=target_model,
            google_api_key=gemini_key,
            temperature=temperature,
            max_retries=2,
            timeout=60,
        )

    if openai_key and ChatOpenAI:
        target_model = model_name or openai_model
        return ChatOpenAI(
            model=target_model,
            api_key=openai_key,
            temperature=temperature,
            max_retries=2,
            timeout=60,
        )

    raise RuntimeError("No LLM API key configured. Provide GEMINI_API_KEY or OPENAI_API_KEY.")


def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code block indicators and trim whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def invoke_structured_json(llm: BaseChatModel, prompt: str, schema_cls: Type[T]) -> T:
    """Invoke the LLM asking for strict JSON matching schema_cls and validate."""
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        f"CRITICAL INSTRUCTION: You MUST return ONLY a single valid JSON object strictly matching this schema:\n"
        f"{schema_json}\n\n"
        f"Do NOT include any commentary, Markdown formatting, or notes outside the JSON."
    )

    try:
        response = llm.invoke(full_prompt)
    except Exception as exc:
        err_str = str(exc)
        if "404" in err_str or "NOT_FOUND" in err_str or "is no longer available" in err_str:
            fallback_model = "gemini-3.5-flash-lite" if getattr(llm, "model", "") != "gemini-3.5-flash-lite" else "gemini-3.8-flash"
            logger.warning("Requested Gemini model not available (%s). Falling back to %s: %s", getattr(llm, "model", ""), fallback_model, exc)
            fallback_llm = get_default_llm(model_name=fallback_model)
            response = fallback_llm.invoke(full_prompt)
        elif "503" in err_str or "UNAVAILABLE" in err_str:
            fallback_model = "gemini-3.5-flash-lite" if getattr(llm, "model", "") != "gemini-3.5-flash-lite" else "gemini-3.5-flash"
            logger.warning("Gemini model capacity spike (%s). Falling back to %s: %s", getattr(llm, "model", ""), fallback_model, exc)
            fallback_llm = get_default_llm(model_name=fallback_model)
            response = fallback_llm.invoke(full_prompt)
        else:
            raise exc

    # 1. Handle mock / FakeLLM / Runnable returning validated model directly
    if isinstance(response, schema_cls):
        return response

    # 2. Handle mock / FakeLLM returning raw dict
    if isinstance(response, dict):
        return schema_cls.model_validate(response)

    # 3. Extract text from content (handles list of parts or string)
    if hasattr(response, "content"):
        if isinstance(response.content, list):
            raw_text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in response.content
            )
        else:
            raw_text = str(response.content)
    else:
        raw_text = str(response)

    clean_text = _clean_json_text(raw_text)

    # Attempt direct json parse
    try:
        data = json.loads(clean_text)
        return schema_cls.model_validate(data)
    except Exception as exc:
        logger.warning("Direct JSON parse failed: %s. Attempting fallback regex extraction.", exc)
        # Attempt to find the outermost JSON object with regex
        match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return schema_cls.model_validate(data)
            except Exception:
                pass
        raise exc
