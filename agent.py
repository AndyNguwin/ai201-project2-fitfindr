"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import json

from tools import (
    ERROR_PREFIX,
    _MODEL,
    _get_groq_client,
    create_fit_card,
    search_listings,
    suggest_outfit,
)


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """Use the LLM to extract structured listing search parameters."""
    prompt = (
        "Extract the clothing search criteria from the user's message. Return a "
        "JSON object with exactly these keys: description, size, max_price. "
        "The description must contain only the item being searched for, without "
        "requests about styling, outfits, captions, or conversational filler. "
        "Use null for a missing size or maximum price. max_price must be a number.\n\n"
        f"User message: {query}"
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You extract structured search criteria for a fashion app.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = (response.choices[0].message.content or "").strip()
    parsed = json.loads(content)

    description = parsed.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("The query did not include an item description.")

    size = parsed.get("size")
    if size is not None:
        size = str(size).strip() or None

    max_price = parsed.get("max_price")
    if max_price is not None:
        max_price = float(max_price)
        if max_price < 0:
            raise ValueError("Maximum price cannot be negative.")

    return {
        "description": description.strip(),
        "size": size.upper() if size else None,
        "max_price": max_price,
    }


def _is_tool_error(result: object) -> bool:
    """Return True when an LLM-backed tool did not produce usable output."""
    return (
        not isinstance(result, str)
        or not result.strip()
        or result.strip().startswith(ERROR_PREFIX)
    )


def _print_state(action: str, key: str, value: object) -> None:
    """Print a labeled session value for tracing state through the agent flow."""
    print(f"[STATE {action}] session[{key!r}] = {value!r}")


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)

    if not isinstance(query, str) or not query.strip():
        session["error"] = "Please describe the clothing item you want to find."
        _print_state("UPDATED", "error", session["error"])
        return session

    try:
        session["parsed"] = _parse_query(query)
    except Exception:
        session["error"] = (
            "I couldn't understand the item, size, or price in that request. "
            "Please try rephrasing it."
        )
        _print_state("UPDATED", "error", session["error"])
        return session

    _print_state("UPDATED", "parsed", session["parsed"])

    try:
        parsed = session["parsed"]
        _print_state("ACCESSED", "parsed", parsed)
        session["search_results"] = search_listings(
            description=parsed["description"],
            size=parsed["size"],
            max_price=parsed["max_price"],
        )
    except Exception:
        session["error"] = "I couldn't search the listings right now. Please try again."
        _print_state("UPDATED", "error", session["error"])
        return session

    if not session["search_results"]:
        session["error"] = (
            "No listings matched your search. Try a different description, size, "
            "or price limit."
        )
        _print_state("UPDATED", "error", session["error"])
        return session

    session["selected_item"] = session["search_results"][0]
    _print_state("UPDATED", "selected_item", session["selected_item"])

    try:
        _print_state("ACCESSED", "selected_item", session["selected_item"])
        outfit = suggest_outfit(session["selected_item"], session["wardrobe"])
    except Exception:
        outfit = None
    if _is_tool_error(outfit):
        session["error"] = "I couldn't suggest an outfit right now. Please try again."
        _print_state("UPDATED", "error", session["error"])
        return session
    session["outfit_suggestion"] = outfit.strip()
    _print_state("UPDATED", "outfit_suggestion", session["outfit_suggestion"])

    try:
        _print_state("ACCESSED", "outfit_suggestion", session["outfit_suggestion"])
        _print_state("ACCESSED", "selected_item", session["selected_item"])
        fit_card = create_fit_card(
            session["outfit_suggestion"], session["selected_item"]
        )
    except Exception:
        fit_card = None
    if _is_tool_error(fit_card):
        session["error"] = "I couldn't create a fit card right now. Please try again."
        _print_state("UPDATED", "error", session["error"])
        return session
    session["fit_card"] = fit_card.strip()
    _print_state("UPDATED", "fit_card", session["fit_card"])

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
