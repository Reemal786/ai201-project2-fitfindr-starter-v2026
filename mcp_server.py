
from mcp.server.fastmcp import FastMCP
from tools import search_listings as _search_listings_impl

mcp = FastMCP("fitfindr", log_level="WARNING")


@mcp.tool()
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search secondhand clothing listings using descriptive keywords,
    an optional clothing size, and an optional maximum price in US dollars.

    Args:
        description: Keywords describing the clothing item to find.
        size: Optional clothing size, such as S, M, or L.
        max_price: Optional maximum price in US dollars, inclusive.

    Returns:
        A list of matching clothing listings ordered by relevance.
        Each listing includes its title, price, size, condition,
        platform, and other item details.
        Returns an empty list [] when no listings match.
    """
    return _search_listings_impl(description, size, max_price)


if __name__ == "__main__":
    mcp.run()
