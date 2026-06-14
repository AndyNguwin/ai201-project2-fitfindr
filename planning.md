# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- This tool will allow the agent to search the available listings of clothing items and filter for specific items based on the inputted description, size, and price.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): keywords that relate to what items the user wants to look for
- `size` (str): a size to filter (like S/M/L/XL or "small") for relating to the item the user wants to search for
- `max_price` (float): the maximum price to filter for relating to the item the user wants to search for

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
- The tool will return a list of item listings that match the filters ranked by relevancy. Each item listing is represented as a dictionary with information/metadata relating to the listing (as shown in the listings.json).
**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
- If there was an error with the tool call, the agent should analyze the parameters it used with the tool and verify it used the correct parameters. It should retry the tool call if it needs to correct its parameters. If the parameters were correct and it returned an empty list of listings, then the agent will immediately stop the loop and tell the user that there were no listings that match the description they gave.
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- This tool will curate and suggest 1 or 2 outfits for the user using a specific clothing item listing with the rest of the user's wardrobe.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): a specific clothing item listing that the user doesn't own yet
- `wardrobe` (dict): all of the clothing items that the user has in their wardrobe to match/style with the new item

**What it returns:**
<!-- Describe the return value -->
- The tool will return a string describing 1-2 outfits that uses the specified new clothing item and the user's wardrobe. If the wardrobe is empty, the tool will return styling tips for the new item instead of outfits.
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
-  If the wardrobe is empty or if no outfit can be suggested, the tool will return styling tips for the new item instead of outfits.
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)
- FitFindr is capable of searching for item listings based on a description provided by the user, suggest outfits with the listings and the user's wardrobe, and create a short captions describing the outfits and listed items to share on social media. If the user asks to search for items, suggest outfits, and create captions, the agent needs to call tools in the order of `search_listings()` -> `suggest_outfit()` for the found listings -> `create_fit_card()` for the suggested outfits. If there were no valid listings found, the agent will say so and immediately stop in the flow rather than continue to the two other tools. If the wardrobe is empty, the agent will just provide suggestions on how to style with the clothing item listings instead of outfits.

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
- The agent needs to first search the available listings for what the user wants to look for using the `search_listings()` function with the description of "vintage graphic tee" and max_price of 30.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
- Assuming the tools work correctly, `search_listings()` will return back a list of item listings (represented as dictionaries) that relate to the query/filtering asked for. For each item listing, the agent will then call `suggest_outfit()` to help the user style with the items found with what they have in their wardrobe. The input will be each item listing dictionary and the user's wardrobe which is already accessible and represented as a dictionary too. If the listings was empty, the agent won't suggest outfits and asks the user for something else to search for. If the wardrobe is empty, the agent will suggest styling tips for the clothing item listings rather than outfits.

**Step 3:**
<!-- Continue until the full interaction is complete -->
- `suggest_outfit()` returns back a string that describes the completed outfit(s) that uses an item listing related to the user's query with their wardrobe. The agent will continue calling `suggest_outfit()` with all of searched listings and update the managed state.

**Final output to user:**
<!-- What does the user actually see at the end? -->
- At the end, if there were listings that match their search, the user will see a list of item listings and matching suggested outfits using the user's wardrobe. At the end, the agent can ask the user if they would like ideas for captions to describe the suggested outfits and items for social media, and it will call `create_fit_card()` if so.
