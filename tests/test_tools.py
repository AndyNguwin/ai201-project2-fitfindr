"""
tests/test_tools.py

Unit tests for the three FitFindr tools, with at least one test per failure mode.

The LLM-backed tools (suggest_outfit, create_fit_card) are tested without hitting
the real Groq API: we monkeypatch tools._get_groq_client so the tests are fast,
deterministic, and don't require an API key. Run with:

    .venv/Scripts/python.exe -m pytest
"""

from unittest.mock import MagicMock

import pytest

from tools import (
    ERROR_PREFIX,
    create_fit_card,
    search_listings,
    suggest_outfit,
)
from utils.data_loader import (
    get_empty_wardrobe,
    get_example_wardrobe,
    load_listings,
)


# ── helpers / fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_item() -> dict:
    """A real listing dict to feed into the LLM-backed tools."""
    return load_listings()[0]


def _fake_groq(content):
    """
    Return a stand-in for tools._get_groq_client that yields a fake Groq client
    whose chat completion returns `content`.
    """
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    client.chat.completions.create.return_value.choices = [choice]
    return lambda: client


def _raising_groq():
    """Return a stand-in for tools._get_groq_client that raises on use."""
    def _factory():
        raise RuntimeError("simulated Groq/API failure")
    return _factory


# ── Tool 1: search_listings ─────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_ranks_relevant_first():
    # Best match for "graphic tee" should genuinely be a tee/graphic item.
    results = search_listings("graphic tee", size=None, max_price=50)
    assert results
    top = results[0]
    haystack = (top["title"] + " " + " ".join(top["style_tags"])).lower()
    assert "tee" in haystack or "graphic" in haystack


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("jacket", size="M", max_price=None)
    # Every returned listing's size should match the requested "M".
    assert all("m" in item["size"].lower() for item in results)


# Failure mode: no listings match the query → empty list, no exception.
def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


# Failure mode: a blank/keyword-less description has nothing to match → empty list.
def test_search_blank_description_returns_empty():
    assert search_listings("", size=None, max_price=None) == []


# Failure mode: unexpected internal error (e.g. data load fails) → empty list, no raise.
def test_search_internal_error_returns_empty(monkeypatch):
    def boom():
        raise RuntimeError("data load failed")
    monkeypatch.setattr("tools.load_listings", boom)
    assert search_listings("anything") == []


# ── Tool 2: suggest_outfit ───────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _fake_groq("Pair it with the baggy jeans."))
    result = suggest_outfit(sample_item, get_example_wardrobe())
    assert not result.startswith(ERROR_PREFIX)
    assert result == "Pair it with the baggy jeans."


# Failure mode: wardrobe is empty → graceful styling advice, NOT an error.
def test_suggest_outfit_empty_wardrobe(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _fake_groq("Here are some styling tips."))
    result = suggest_outfit(sample_item, get_empty_wardrobe())
    assert not result.startswith(ERROR_PREFIX)
    assert result == "Here are some styling tips."


# Failure mode: no item provided → error string with prefix.
def test_suggest_outfit_missing_item():
    result = suggest_outfit(None, get_example_wardrobe())
    assert result.startswith(ERROR_PREFIX)


# Failure mode: LLM/API call raises → error string with prefix (never raises).
def test_suggest_outfit_llm_error(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _raising_groq())
    result = suggest_outfit(sample_item, get_example_wardrobe())
    assert result.startswith(ERROR_PREFIX)


# Failure mode: LLM returns an empty/blank response → error string with prefix.
def test_suggest_outfit_empty_response(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _fake_groq(""))
    result = suggest_outfit(sample_item, get_example_wardrobe())
    assert result.startswith(ERROR_PREFIX)


# ── Tool 3: create_fit_card ──────────────────────────────────────────────────────

def test_create_fit_card_success(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _fake_groq("Thrifted and obsessed!"))
    result = create_fit_card("baggy jeans + graphic tee", sample_item)
    assert not result.startswith(ERROR_PREFIX)
    assert result == "Thrifted and obsessed!"


# Failure mode: outfit string is empty → error string with prefix.
def test_create_fit_card_empty_outfit(sample_item):
    assert create_fit_card("", sample_item).startswith(ERROR_PREFIX)


# Failure mode: outfit string is whitespace-only → error string with prefix.
def test_create_fit_card_whitespace_outfit(sample_item):
    assert create_fit_card("   ", sample_item).startswith(ERROR_PREFIX)


# Failure mode: no item provided → error string with prefix.
def test_create_fit_card_missing_item():
    assert create_fit_card("a cute outfit", None).startswith(ERROR_PREFIX)


# Failure mode: LLM/API call raises → error string with prefix (never raises).
def test_create_fit_card_llm_error(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _raising_groq())
    assert create_fit_card("baggy jeans + tee", sample_item).startswith(ERROR_PREFIX)


# Failure mode: LLM returns an empty/blank response → error string with prefix.
def test_create_fit_card_empty_response(monkeypatch, sample_item):
    monkeypatch.setattr("tools._get_groq_client", _fake_groq(""))
    assert create_fit_card("baggy jeans + tee", sample_item).startswith(ERROR_PREFIX)
