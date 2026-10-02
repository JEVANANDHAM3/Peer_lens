from __future__ import annotations

import pytest

from backend.agents.clarity_agent import ChatGoogleGenerativeAI as ClarityGemini
from backend.agents.clarity_agent import get_default_llm as get_clarity_llm
from backend.agents.meta_agent import MetaReviewerAgent
from backend.agents.novelty_agent import NoveltyReviewerAgent
from backend.agents.rigor_agent import ChatGoogleGenerativeAI as RigorGemini
from backend.agents.rigor_agent import get_default_llm as get_rigor_llm


@pytest.mark.parametrize(
    "getter, provider_cls",
    [
        (get_rigor_llm, RigorGemini),
        (get_clarity_llm, ClarityGemini),
    ],
)
def test_default_llm_uses_gemini_when_gemini_key_exists(monkeypatch, getter, provider_cls):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    llm = getter()

    assert llm is not None
    assert isinstance(llm, provider_cls)
    assert hasattr(llm, "model")


def test_novelty_agent_is_not_tied_to_llm_provider(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = NoveltyReviewerAgent()

    assert agent is not None
    assert hasattr(agent, "retriever")


def test_meta_agent_is_independent_and_does_not_require_llm(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = MetaReviewerAgent()

    assert agent is not None
    assert agent.llm is None
