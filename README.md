# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

FitFindr is a secondhand fashion assistant that helps users find clothing listings that match a natural-language request and style the selected item with pieces they already own. It parses the user's request for a clothing description, size, and maximum price, then searches and ranks matching secondhand listings. When a match is found, FitFindr selects an item, suggests one or two outfits using the user's wardrobe, and creates a short social-media-style fit card. If no listings match, the agent stops early and tells the user which search constraints they can change instead of continuing with the remaining tools.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

**What it does:** Searches the secondhand listings dataset for items that match the user's description and optional size and maximum price filters, ranking the strongest keyword matches first.
**Inputs:** `description` (str), `size` (str | None), `max_price` (float | None). Size matching is case-insensitive and matches complete size components rather than arbitrary substrings so, for example, `M` can match `S/M` without `S` incorrectly matching `US 9`.
**Returns:** A list of matching listing dictionaries, ordered from highest keyword-overlap score to lowest, with at most `config.SEARCH_RESULT_LIMIT` results. Each dictionary contains the listing's `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
**When it has nothing:** Returns an empty list `[]` when no listings satisfy the filters and description match.

### `suggest_outfit`

**What it does:** Creates one or two outfit suggestions for the selected secondhand item using pieces from the user's existing wardrobe.
**Inputs:** `new_item` (dict), containing the selected listing, and `wardrobe` (dict), containing an `items` list of clothing the user owns.
**Returns:** A non-empty string containing outfit suggestions that incorporate the selected item and, when available, specific pieces from the user's wardrobe.
**When it has nothing:** If the wardrobe's `items` list is empty, returns general styling advice for the selected item instead of returning an empty string or raising an error.

### `create_fit_card`

**What it does:** Creates a short, social-media-style caption describing the selected thrifted item and the suggested outfit.
**Inputs:** `outfit` (str), containing the suggestion returned by `suggest_outfit`, and `new_item` (dict), containing the selected listing.
**Returns:** A two-to-four sentence caption that mentions the selected item, its price, its platform, and the outfit's overall vibe.
**When it has nothing:** If `outfit` is empty or contains only whitespace, returns a descriptive message explaining that a fit card cannot be created without an outfit suggestion.
---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, the agent stores an error message telling the user to change the description, size, or maximum price and stops. Otherwise, it selects the first search result, passes it to `suggest_outfit`, and then passes the resulting outfit suggestion to `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** The query is parsed using regular expressions and string cleanup. The parser extracts an explicitly stated size and maximum price, removes those phrases and common filler words from the query, and uses the remaining text as the listing description.

**What moves through the session:** The original query is stored in `session["query"]`, followed by the parsed search values in `session["parsed"]`, the search results in `session["search_results"]`, the chosen listing in `session["selected_item"]`, the outfit returned by `suggest_outfit` in `session["outfit_suggestion"]`, and finally the generated caption in `session["fit_card"]`. Each tool reads the result of the previous step back from the session.
---

## Sample Run

### Full Query

**Command:**

```text
python app.py ask "vintage graphic tee under $30"
```

**Output:**

```text
Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

Outfit:   Here are two ways to style your new Y2K butterfly baby tee using pieces from your existing wardrobe:

Outfit 1: Classic Y2K Streetwear
- Bottoms: Baggy straight-leg jeans (dark wash)
- Shoes: Chunky white sneakers
- Accessories: Black crossbody bag
- Why it works: The fitted crop of the baby tee balances out the baggy silhouette of the high-waisted dark denim for an authentic early-2000s look. Finish with your chunky sneakers and crossbody bag for an easy everyday outfit.

Outfit 2: Edgy Contrast
- Outerwear: Vintage black denim jacket
- Bottoms: Wide-leg khaki trousers
- Shoes: Black combat boots
- Accessories: Brown leather belt
- Why it works: Pairing the sweet, pastel butterfly graphic with your black combat boots and slightly cropped denim jacket adds a cool grunge contrast. Use the brown belt to tie the khaki trousers together and anchor the look.

Fit card: Threw on my new Y2K baby tee with a butterfly print that I just scored on depop for eighteen dollars, and I'm honestly obsessed with how it looks. Paired it with my baggy dark wash jeans and chunky white sneakers for that classic early-2000s streetwear vibe. It's giving total nostalgic energy and is definitely about to be my go-to weekend fit!

0 model calls this session, 2 served from cache
```

### Per-Tool Tests

**1. `search_listings`**

```text
python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
```

The search returned matching secondhand listings including Y2K Baby Tee — Butterfly Print ($18), Graphic Tee — 2003 Tour Bootleg Style ($24), and Vintage Band Tee ($19). Every returned listing was at or below the $30 maximum price.

**2. `suggest_outfit`**

```text
python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
```

The tool returned two outfit suggestions for the Vintage Levi's 501 Jeans and referenced specific pieces from the example wardrobe, including the white ribbed tank, vintage black denim jacket, chunky white sneakers, black crossbody bag, oversized grey crewneck, black combat boots, and brown leather belt.

**3. `create_fit_card`**

```text
python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
```

```text
Pulled these vintage Levi's 501 jeans out of my closet for a casual coffee run today, paired with crisp white sneakers for that effortlessly cool streetwear vibe. They have the best medium wash with lived-in fading at the knees that just can't be faked. Grabbed this exact pair on depop for $38.0 and I honestly haven't taken them off since.
```

---

## How I Used AI

### 1. Implementing and testing `search_listings`

I asked AI for help implementing `search_listings` based on the starter TODOs, especially how to filter by size without using unsafe substring matching. AI suggested separating listing sizes into components and checking for an exact size match, along with using keyword overlap to rank results. I kept the exact size-matching approach and tested the function with `"graphic tee"` and a $30 maximum price to confirm that relevant results were returned and every result respected the price limit.

### 2. Handling edge cases in the generative tools

I asked AI for help implementing and testing `suggest_outfit` and `create_fit_card`, including what should happen when the wardrobe or outfit input is empty. AI suggested explicitly handling those cases before making unnecessary model calls: `suggest_outfit` provides general styling advice when the wardrobe is empty, while `create_fit_card` returns an explanatory message when no outfit is provided. I kept these guards and tested both the normal and empty-input paths before connecting the tools through the planning loop.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
