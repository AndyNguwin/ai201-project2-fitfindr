"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

# Common words that carry no search signal — dropped when extracting keywords.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "with", "in", "on", "to",
    "my", "me", "i", "im", "looking", "want", "need", "some", "any", "that",
    "this", "is", "are", "it", "something", "under", "size", "price",
}


def _keywords(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, and drop stopwords / 1-char tokens."""
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


def _size_matches(query_size: str, listing_size: str) -> bool:
    """
    Case-insensitive size match. The listing size is split into tokens so a
    query like "M" matches "S/M" or "M/L" without matching letters buried
    inside words (e.g. "M" should not match "oversized").
    """
    q = query_size.strip().lower()
    if not q:
        return True
    listing = listing_size.lower()
    tokens = [t for t in re.split(r"[\s/()]+", listing) if t]
    if q in tokens:
        return True
    # Allow multi-character queries to match as a substring (e.g. "xl" in "xl (oversized)").
    return len(q) >= 2 and q in listing


def _score(keywords: list[str], listing: dict) -> int:
    """
    Score a listing by how many query keywords appear in its searchable text.
    Matches in the title and style_tags are weighted higher since they are the
    strongest relevance signals.
    """
    weighted_high = " ".join([
        listing.get("title", ""),
        " ".join(listing.get("style_tags", [])),
    ]).lower()
    weighted_low = " ".join([
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("colors", [])),
        listing.get("brand") or "",
    ]).lower()

    score = 0
    for kw in keywords:
        if kw in weighted_high:
            score += 2
        elif kw in weighted_low:
            score += 1
    return score


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    try:
        listings = load_listings()

        # 1. Filter by price and size first (cheap, exact constraints).
        filtered = []
        for item in listings:
            if max_price is not None and item.get("price", 0) > max_price:
                continue
            if size and not _size_matches(size, item.get("size", "")):
                continue
            filtered.append(item)

        # 2. Score remaining listings by keyword overlap with the description.
        #    The description is the relevance signal — listings that don't match
        #    it score 0 and are dropped, so a query with no matches (including a
        #    blank/keyword-less description) naturally returns an empty list.
        keywords = _keywords(description or "")
        scored = [(item, _score(keywords, item)) for item in filtered]

        # 3. Drop zero-score listings, then sort by score (desc), price (asc) for ties.
        matches = [(item, s) for item, s in scored if s > 0]
        matches.sort(key=lambda pair: (-pair[1], pair[0].get("price", 0)))

        return [item for item, _ in matches]
    except Exception:
        # Any unexpected failure (e.g. data load error) returns no results.
        return []


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Replace this with your implementation
    return ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    return ""


# ── Manual tests ──────────────────────────────────────────────────────────────
# Run each tool in isolation:  .venv/Scripts/python.exe tools.py

def _print_listings(label: str, results: list[dict]) -> None:
    print(f"=== {label} ({len(results)} results) ===")
    for r in results[:6]:
        print(f"  {r['id']}  ${r['price']:<6} {r['size']:<20} {r['title']}")
    print()


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    # ── Tool 1: search_listings ──
    print("\n##### search_listings #####\n")
    _print_listings("vintage graphic tee under $30",
                    search_listings("vintage graphic tee", max_price=30))
    _print_listings("90s track jacket, size M",
                    search_listings("90s track jacket", size="M"))
    _print_listings("platform sneakers, size 8",
                    search_listings("platform sneakers", size="8"))
    _print_listings("no-results test (designer ballgown XXS under $5)",
                    search_listings("designer ballgown", size="XXS", max_price=5))

    # ── Tool 2: suggest_outfit ── (uncomment once implemented)
    # print("\n##### suggest_outfit #####\n")
    # item = search_listings("vintage graphic tee", max_price=30)[0]
    # print("With example wardrobe:\n", suggest_outfit(item, get_example_wardrobe()), "\n")
    # print("With empty wardrobe:\n", suggest_outfit(item, get_empty_wardrobe()), "\n")

    # ── Tool 3: create_fit_card ── (uncomment once implemented)
    # print("\n##### create_fit_card #####\n")
    # outfit = suggest_outfit(item, get_example_wardrobe())
    # print(create_fit_card(outfit, item), "\n")
    # print("Empty outfit guard:\n", create_fit_card("", item), "\n")
