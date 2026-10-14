
"""
The FitFindr planning loop.

Searches through MCP, suggests outfits, and creates fit cards.
Includes tracing and error handling.
"""

import re

import config
import trace
from mcp_client import call_tool, MCPError
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable


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
            price_pattern, "",
            description, flags=re.IGNORECASE
        )

    size_pattern = r"\bsize\s+([A-Za-z0-9]+(?:/[A-Za-z0-9]+)?)"
    size_match = re.search(
        size_pattern, query, re.IGNORECASE
    )

    size = None

    if size_match:
        size = size_match.group(1)
        description = re.sub(
            size_pattern, "",
            description, flags=re.IGNORECASE
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


def run_agent(query: str, wardrobe: dict) -> dict:
    trace.start_trace()
    session = new_session(query, wardrobe)
    iteration_count = 0

    # Step 1: Parse the query
    iteration_count += 1
    trace.check_iterations(iteration_count)

    session["parsed"] = parse_query(session["query"])

    trace.step(
        "parse_query",
        inputs=query,
        returned=session["parsed"],
    )

    # Step 2: Search listings through MCP
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

        trace.step(
            "search_listings (via MCP)",
            inputs=parsed,
            returned=session["search_results"],
        )

    except MCPError as exc:
        session["error"] = (
            "Clothing search is temporarily unavailable. "
            "Check the MCP server and try again. "
            f"Details: {exc}"
        )

        trace.step(
            "search_listings (via MCP)",
            inputs=parsed,
            returned=str(exc),
            note="MCP error: stopping",
        )
        return session

    # Branch: no matching listings
    if not session["search_results"]:
        session["error"] = (
            "No matching listings were found. "
            "Try changing the description, using a different "
            "size, or increasing your maximum price."
        )

        trace.step(
            "search_results_check",
            returned=session["search_results"],
            note="branch: empty search, stopping",
        )
        return session

    # Step 3: Select an item
    iteration_count += 1
    trace.check_iterations(iteration_count)

    session["selected_item"] = session["search_results"][0]

    trace.step(
        "select_item",
        returned=session["selected_item"],
        note="selected first matching listing",
    )

    # Step 4: Suggest outfit
    iteration_count += 1
    trace.check_iterations(iteration_count)

    try:
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"],
            session["wardrobe"],
        )

        trace.step(
            "suggest_outfit",
            inputs={
                "item": session["selected_item"],
                "wardrobe": session["wardrobe"],
            },
            returned=session["outfit_suggestion"],
        )

    except ModelUnavailable as exc:
        session["error"] = (
            "Outfit suggestions are temporarily unavailable. "
            "Check your model configuration or API connection "
            "and try again."
        )

        trace.step(
            "suggest_outfit",
            returned=str(exc),
            note="model unavailable: stopping",
        )
        return session

    # Step 5: Create fit card
    iteration_count += 1
    trace.check_iterations(iteration_count)

    try:
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"],
            session["selected_item"],
        )

        trace.step(
            "create_fit_card",
            inputs={
                "outfit": session["outfit_suggestion"],
                "item": session["selected_item"],
            },
            returned=session["fit_card"],
        )

    except ModelUnavailable as exc:
        session["error"] = (
            "The outfit was generated, but the fit card "
            "could not be created because the model is "
            "unavailable. Check your API connection "
            "and try again."
        )

        trace.step(
            "create_fit_card",
            returned=str(exc),
            note="model unavailable: stopping",
        )
        return session

    return session


def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card: {session['fit_card']!r}")
        return

    item = session["selected_item"] or {}

    print(
        f"  found: {item.get('title')} — "
        f"${item.get('price')} on {item.get('platform')}"
    )
    print(f"  outfit: {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Matching query ===")
    _show(
        run_agent(
            "looking for a vintage graphic tee under $30",
            get_example_wardrobe(),
        )
    )

    print("\n=== Nonmatching query ===")
    _show(
        run_agent(
            "designer ballgown size XXS under $5",
            get_example_wardrobe(),
        )
    )
