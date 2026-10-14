
"""
The FitFindr planning loop.

Uses MCP for clothing searches and local tools for outfit suggestions
and fit-card creation.
"""

import re

import config
import trace
from mcp_client import call_tool, MCPError
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── Session state ─────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── Query parsing ─────────────────────────────────────────────────

def parse_query(query: str) -> dict:
    description = query.strip()

    price_pattern = (
        r"\b(?:under|below|max(?:imum)?)\s*\$?\s*"
        r"(\d+(?:\.\d+)?)"
    )

    price_match = re.search(
        price_pattern, query, re.IGNORECASE
    )

    max_price = None

    if price_match:
        max_price = float(price_match.group(1))
        description = re.sub(
            price_pattern,
            "",
            description,
            flags=re.IGNORECASE,
        )

    size_pattern = r"\bsize\s+([A-Za-z0-9]+(?:/[A-Za-z0-9]+)?)"
    size_match = re.search(
        size_pattern, query, re.IGNORECASE
    )

    size = None

    if size_match:
        size = size_match.group(1)
        description = re.sub(
            size_pattern,
            "",
            description,
            flags=re.IGNORECASE,
        )

    description = re.sub(
        r"\b(?:looking for|look for|find me|find|search for|i want|i need)\b",
        "",
        description,
        flags=re.IGNORECASE,
    )

    description = description.replace(",", " ")
    description = " ".join(description.split()).strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── Planning loop ─────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    session = new_session(query, wardrobe)
    iteration_count = 0

    # Step 1: Parse query
    iteration_count += 1
    trace.check_iterations(iteration_count)

    session["parsed"] = parse_query(session["query"])

    # Step 2: Search through MCP
    iteration_count += 1
    trace.check_iterations(iteration_count)

    parsed = session["parsed"]

    try:
        session["search_results"] = call_tool(
            "search_listings",
            {
                "description": parsed["description"],
                "size": parsed["size"],
                "max_price": parsed["max_price"],
            },
        )
    except MCPError as exc:
        session["error"] = (
            "Clothing search is temporarily unavailable. "
            "Check the MCP server and try again. "
            f"Details: {exc}"
        )
        return session

    # Stop if nothing matches
    if not session["search_results"]:
        session["error"] = (
            "No matching listings were found. "
            "Try changing the description, using a different "
            "size, or increasing your maximum price."
        )
        return session

    # Step 3: Select first result
    iteration_count += 1
    trace.check_iterations(iteration_count)

    session["selected_item"] = session["search_results"][0]

    # Step 4: Suggest outfit
    iteration_count += 1
    trace.check_iterations(iteration_count)

    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"],
        session["wardrobe"],
    )

    # Step 5: Create fit card
    iteration_count += 1
    trace.check_iterations(iteration_count)

    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"],
    )

    return session


# ── Run directly ──────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(
            f"  fit_card is {session['fit_card']!r} "
            "— it should still be None here"
        )
        return

    item = session["selected_item"] or {}

    print(
        f"  found:    {item.get('title')} — "
        f"${item.get('price')} on {item.get('platform')}"
    )

    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(
        run_agent(
            query="looking for a vintage graphic tee under $30",
            wardrobe=get_example_wardrobe(),
        )
    )

    print("\n=== A query it can't ===")
    _show(
        run_agent(
            query="designer ballgown size XXS under $5",
            wardrobe=get_example_wardrobe(),
        )
    )

    print(
        "\nThe second one should stop before the fit card. "
        "If both paths look the same, the branch isn't working."
    )
