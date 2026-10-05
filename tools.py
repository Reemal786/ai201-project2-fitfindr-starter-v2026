"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """

    listings = load_listings()

    # Convert the user's description into lowercase search words.
    search_words = set(description.lower().split())

    matches = []

    for listing in listings:

        # Skip listings above the user's maximum price.
        if max_price is not None and listing["price"] > max_price:
            continue

        # Filter by size when the user provides one.
        if size is not None:
            requested_size = size.lower().strip()
            listing_size = listing["size"].lower().strip()

            # Split combined sizes such as "S/M" into individual size values.
            # This avoids incorrect substring matches such as "s" matching
            # the "s" in "US 9".
            size_parts = [
                part.strip()
                for part in listing_size
                .replace("(", "/")
                .replace(")", "")
                .split("/")
            ]

            if requested_size not in size_parts:
                continue

        # Combine fields that may contain words related to the user's search.
        # Some listings have no brand, so None is converted to an empty string.
        searchable_parts = [
            listing["title"] or "",
            listing["description"] or "",
            listing["category"] or "",
            " ".join(listing["style_tags"] or []),
            " ".join(listing["colors"] or []),
            listing["brand"] or "",
            listing["platform"] or "",
        ]

        searchable_text = " ".join(searchable_parts).lower()

        # Score the listing based on how many description words appear in it.
        score = sum(
            1
            for word in search_words
            if word in searchable_text
        )

        # A listing must match at least one search word.
        if score > 0:
            matches.append((score, listing))

    # Put listings with the highest keyword-overlap score first.
    matches.sort(
        key=lambda match: match[0],
        reverse=True,
    )

    # Remove the scores and return only the listing dictionaries.
    return [
        listing
        for score, listing in matches[:config.SEARCH_RESULT_LIMIT]
    ]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """

    wardrobe_items = wardrobe.get("items", [])

    # If the wardrobe is empty, still provide useful general styling advice.
    if not wardrobe_items:
        prompt = f"""
You are helping a user style a secondhand clothing item.

New item:
Title: {new_item.get("title", "")}
Description: {new_item.get("description", "")}
Category: {new_item.get("category", "")}
Colors: {", ".join(new_item.get("colors", []))}
Style tags: {", ".join(new_item.get("style_tags", []))}

The user's wardrobe is empty, so do not claim they already own any specific
pieces. Suggest one or two general outfit ideas for styling this item.
Keep the suggestions concise, practical, and specific.
"""

        return generate(prompt)

    # Format the user's existing wardrobe into readable lines for the model.
    wardrobe_lines = []

    for item in wardrobe_items:
        name = item.get("name", "Unnamed item")
        category = item.get("category", "")
        colors = ", ".join(item.get("colors", []))
        style_tags = ", ".join(item.get("style_tags", []))
        notes = item.get("notes", "")

        wardrobe_lines.append(
            f"- {name} | category: {category} | colors: {colors} | "
            f"style: {style_tags} | notes: {notes}"
        )

    wardrobe_text = "\n".join(wardrobe_lines)

    prompt = f"""
You are helping a user style a secondhand clothing item using pieces they
already own.

New item:
Title: {new_item.get("title", "")}
Description: {new_item.get("description", "")}
Category: {new_item.get("category", "")}
Colors: {", ".join(new_item.get("colors", []))}
Style tags: {", ".join(new_item.get("style_tags", []))}

User's wardrobe:
{wardrobe_text}

Suggest one or two outfits that combine the new item with specific pieces from
the user's wardrobe. Name the wardrobe pieces you use so the user can identify
them. Keep the suggestions concise, practical, and specific.
"""

    return generate(prompt)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """

    # Stop before calling the model if there is no outfit suggestion.
    if not outfit or not outfit.strip():
        return (
            "A fit card cannot be created because there is no outfit "
            "suggestion to describe."
        )

    title = new_item.get("title", "the selected item")
    price = new_item.get("price")
    platform = new_item.get("platform", "the listing platform")
    description = new_item.get("description", "")
    colors = ", ".join(new_item.get("colors", []))
    style_tags = ", ".join(new_item.get("style_tags", []))

    prompt = f"""
Write a short social-media-style fit card for a secondhand fashion find.

Selected item:
Title: {title}
Description: {description}
Price: ${price}
Platform: {platform}
Colors: {colors}
Style tags: {style_tags}

Outfit suggestion:
{outfit}

Write a caption that:
- is 2 to 4 sentences long
- sounds like something a person would actually post
- mentions the selected item
- mentions its price (${price}) exactly once
- mentions the platform ({platform}) exactly once
- describes the specific vibe of the outfit
- uses the outfit suggestion to make the caption specific
- does not sound like a product listing or advertisement

Return only the caption.
"""

    return generate(prompt)