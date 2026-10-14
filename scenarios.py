
"""
Evaluation scenarios for FitFindr — Unit 4, Milestone 3.

Each acceptance criterion has one scenario.
run_eval.py runs each scenario five times.

The empty wardrobe scenario is an additional diagnostic.
"""

SCENARIOS = [
    {
        # Criterion 1: Matching query completes all three tools.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # Criterion 2: Impossible query stops before suggest_outfit.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3: Selected item ID matches the item
        # passed to suggest_outfit.
        "name": "selected item state consistency",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4: Fit card mentions the item and its price.
        "name": "fit card item and price accuracy",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Criterion 5: Every returned listing respects
        # the requested maximum price.
        "name": "maximum price compliance",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # Additional diagnostic: Empty wardrobe handling.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Check scenarios for missing or invalid fields."""
    problems = []

    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")

        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe "
                f"{scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )

    return problems
