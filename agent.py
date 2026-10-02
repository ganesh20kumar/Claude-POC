"""
Agentic AI Example — With Custom Tools
----------------------------------------
This agent has THREE types of tools:

  1. web_search    — built-in Anthropic tool, runs on their servers
  2. calculator    — YOUR OWN Python function, runs on your computer
  3. get_weather   — YOUR OWN tool that calls the OpenWeatherMap API

When you ask a question, Claude decides which tool(s) to use,
calls them, reads the results, and gives you a final answer.

Setup for the weather tool:
  1. Sign up free at https://openweathermap.org/api
  2. Go to "API keys" in your account and copy your key
  3. Set it: export OPENWEATHER_API_KEY="your-key-here"

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
import urllib.request
import urllib.parse
import json
import anthropic

# ---------------------------------------------------------------------------
# Step 1: Create the AI client (our connection to Claude)
# ---------------------------------------------------------------------------
client = anthropic.Anthropic()


# ---------------------------------------------------------------------------
# Step 2A: Define YOUR CUSTOM TOOL — a weather checker
#
# We call the free OpenWeatherMap API to get real, live weather data.
# Claude doesn't know how to call APIs — that's YOUR job as the developer.
# Claude just says "I need weather for Paris" and your function does the work.
# ---------------------------------------------------------------------------

WEATHER_TOOL = {
    "name": "get_weather",
    "description": (
        "Get the current real-time weather for any city in the world. "
        "Use this when the user asks about weather, temperature, or climate "
        "in a specific location."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The city name, e.g. 'London', 'Tokyo', 'New York'",
            },
            "units": {
                "type": "string",
                "enum": ["metric", "imperial"],
                "description": "Temperature unit: 'metric' for Celsius, 'imperial' for Fahrenheit",
            },
        },
        "required": ["city"],
    },
}

def run_get_weather(city: str, units: str = "metric") -> str:
    """
    Call the OpenWeatherMap API and return current weather as a string.
    Requires OPENWEATHER_API_KEY environment variable.
    """
    print(f"  → Weather API called for: {city} ({units})")

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return (
            "Error: OPENWEATHER_API_KEY is not set. "
            "Get a free key at https://openweathermap.org/api "
            "then run: export OPENWEATHER_API_KEY='your-key-here'"
        )

    # Build the API URL
    params = urllib.parse.urlencode({
        "q": city,
        "appid": api_key,
        "units": units,
    })
    url = f"https://api.openweathermap.org/data/2.5/weather?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"City '{city}' not found. Try a different spelling."
        if e.code == 401:
            return "Invalid API key. Check your OPENWEATHER_API_KEY."
        return f"API error: HTTP {e.code}"
    except Exception as e:
        return f"Failed to fetch weather: {e}"

    # Pull out the fields we care about
    temp      = data["main"]["temp"]
    feels     = data["main"]["feels_like"]
    humidity  = data["main"]["humidity"]
    desc      = data["weather"][0]["description"].capitalize()
    wind_spd  = data["wind"]["speed"]
    unit_sym  = "°C" if units == "metric" else "°F"
    wind_unit = "m/s" if units == "metric" else "mph"

    return (
        f"Weather in {data['name']}, {data['sys']['country']}:\n"
        f"  Condition : {desc}\n"
        f"  Temperature: {temp}{unit_sym} (feels like {feels}{unit_sym})\n"
        f"  Humidity  : {humidity}%\n"
        f"  Wind      : {wind_spd} {wind_unit}"
    )


# ---------------------------------------------------------------------------
# Step 2B: Define YOUR CUSTOM TOOL — a calculator
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
# Step 2C: All tools the agent can use (mix of built-in and custom)
# ---------------------------------------------------------------------------
tools = [
    # Built-in Anthropic tool — runs on their servers, no code needed from us
    {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 3,
    },
    # Our custom tools — run on OUR computer when Claude calls them
    CALCULATOR_TOOL,
    WEATHER_TOOL,
]

# Map tool names to the functions that handle them
CUSTOM_TOOL_HANDLERS = {
    "calculator": run_calculator,
    "get_weather": run_get_weather,
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
            model="claude-sonnet-4-6",
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
# Step 4: Interactive chat loop — type your own questions!
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set your ANTHROPIC_API_KEY environment variable.")
        print("  set ANTHROPIC_API_KEY=your-key-here  (Windows)")
        exit(1)

    print("\n" + "="*60)
    print("  Agentic AI Assistant")
    print("  Tools available: weather, calculator, web search")
    print("  Type 'quit' or 'exit' to stop")
    print("="*60)
    print("\nExample questions you can try:")
    print("  - What is the weather in Mumbai?")
    print("  - What is 15% of 8500?")
    print("  - Is it warmer in Dubai or Singapore right now?")
    print("  - What is the square root of 144?")
    print("  - Search for the latest news on AI agents")
    print()

    # Keep asking questions until the user types 'quit'
    while True:
        # Get input from the user
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        # Exit if the user types quit or exit
        if question.lower() in ("quit", "exit", "q", "bye"):
            print("Goodbye!")
            break

        # Skip empty input
        if not question:
            print("Please type a question.")
            continue

        # Send the question to the agent
        ask_agent(question)
        print()
