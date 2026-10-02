"""
Agentic AI Example — With Custom Tools
----------------------------------------
This agent has TWO types of tools:

  1. web_search  — built-in Anthropic tool, runs on their servers
  2. calculator  — YOUR OWN Python function, runs on your computer

When you ask a question, Claude decides which tool to use (or both!),
calls them, reads the results, and gives you a final answer.

The core agentic loop:
  You give a goal
       ↓
  Claude thinks: "What tool do I need?"
       ↓
  Tool runs → result comes back
       ↓
  Claude reads result, thinks again
       ↓
  Claude says "Done!" → final answer
"""

import os
import math
import anthropic

# ---------------------------------------------------------------------------
# Step 1: Create the AI client (our connection to Claude)
# ---------------------------------------------------------------------------
client = anthropic.Anthropic()


# ---------------------------------------------------------------------------
# Step 2A: Define YOUR CUSTOM TOOL — a calculator
#
# A custom tool has two parts:
#   (a) The DESCRIPTION — tells Claude what the tool does and when to use it
#   (b) The FUNCTION    — the actual Python code that runs when Claude calls it
# ---------------------------------------------------------------------------

# (a) DESCRIPTION — Claude reads this to understand the tool
CALCULATOR_TOOL = {
    "name": "calculator",
    "description": (
        "Perform mathematical calculations. Use this for any math problem: "
        "arithmetic, percentages, square roots, powers, etc. "
        "Always use this tool instead of trying to calculate in your head."
    ),
    # The 'input_schema' tells Claude exactly what inputs to send.
    # It's like a form Claude must fill out before calling the tool.
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A valid Python math expression, e.g. '2 + 2', '15 * 7', 'math.sqrt(144)'",
            }
        },
        "required": ["expression"],  # Claude MUST provide this field
    },
}

# (b) FUNCTION — the actual code that runs
def run_calculator(expression: str) -> str:
    """
    Safely evaluate a math expression and return the result.
    This is YOUR code — Claude doesn't see it, it just sees the result.
    """
    print(f"  → Calculator called with: {expression}")
    try:
        # We allow math functions like math.sqrt(), math.pi, etc.
        allowed = {"math": math, "__builtins__": {}}
        result = eval(expression, allowed)  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


# ---------------------------------------------------------------------------
# Step 2B: All tools the agent can use (mix of built-in and custom)
# ---------------------------------------------------------------------------
tools = [
    # Built-in Anthropic tool — runs on their servers, no code needed from us
    {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 3,
    },
    # Our custom tool — runs on OUR computer when Claude calls it
    CALCULATOR_TOOL,
]

# Map tool names to the functions that handle them
# When Claude calls "calculator", we run run_calculator()
CUSTOM_TOOL_HANDLERS = {
    "calculator": run_calculator,
}


# ---------------------------------------------------------------------------
# Step 3: The Agent Loop
# ---------------------------------------------------------------------------
def ask_agent(question: str) -> str:
    """
    Send a question to the agent. It will think, use tools as needed,
    and return a final answer.
    """
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": question}]

    while True:
        print("\n[Agent is thinking...]")

        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        stop_reason = response.stop_reason

        # ── Case 1: Claude is done, give the final answer ──────────────────
        if stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n[Final Answer]\n{block.text}")
                    return block.text

        # ── Case 2: Claude wants to use a tool ─────────────────────────────
        elif stop_reason == "tool_use":

            # Add Claude's response (with its tool request) to history
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []

            for block in response.content:

                # ── Custom tool call (e.g. "calculator") ───────────────────
                # When Claude calls a custom tool, WE run the function and
                # send the result back. Claude is waiting for our answer.
                if block.type == "tool_use" and block.name in CUSTOM_TOOL_HANDLERS:
                    print(f"\n[Agent calling custom tool: '{block.name}']")

                    # Look up and run the Python function
                    handler = CUSTOM_TOOL_HANDLERS[block.name]
                    result = handler(**block.input)   # pass Claude's inputs to our function

                    # Package the result to send back to Claude
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,      # links back to Claude's request
                        "content": result,            # our function's return value
                    })

                # ── Server tool result (web_search result came back inline) ─
                elif block.type == "web_search_tool_result":
                    print("\n[Agent received web search results]")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                    })

                elif block.type == "tool_use":
                    # Server-side tool called but result not yet inline
                    print(f"\n[Agent calling server tool: '{block.name}']")

            # If we have results from custom tools, send them back to Claude
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                # Server tools (like web_search) sometimes return results
                # embedded in the same response — pass them forward
                messages.append({"role": "user", "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": b.id,
                        "content": "Search completed. Results are in the previous message.",
                    }
                    for b in response.content if b.type == "tool_use"
                ]})

        else:
            print(f"[Unexpected stop reason: {stop_reason}]")
            break

    return "Agent could not produce an answer."


# ---------------------------------------------------------------------------
# Step 4: Run the agent with questions that need different tools
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set your ANTHROPIC_API_KEY environment variable.")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)

    questions = [
        # This needs the calculator tool
        "If I invest $5,000 at 8% annual interest for 10 years, "
        "how much will I have? (Use compound interest: A = P * (1 + r)^t)",

        # This needs the web search tool
        "What is the current population of India?",

        # This might need both tools!
        "Search for the GDP of USA in 2024 and then calculate what 3.5% of it is.",
    ]

    for question in questions:
        ask_agent(question)
        print("\n")
