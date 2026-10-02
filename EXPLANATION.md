# How agent.py Works — A Complete Explanation

## The Big Picture

The file is split into 4 sections:

```
Section 1 → Connect to Claude (the brain)
Section 2 → Define the tools (the hands)
Section 3 → The agent loop (the thinking engine)
Section 4 → The chat interface (you talk to it)
```

---

## Section 1 — Imports & Client (lines 30–40)

```python
import os, math, urllib.request, urllib.parse, json, anthropic

client = anthropic.Anthropic()
```

| Import | Purpose |
|---|---|
| `os` | Reads environment variables like `ANTHROPIC_API_KEY` |
| `math` | Lets the calculator use `math.sqrt()`, `math.pi`, etc. |
| `urllib` | Makes HTTP calls to the OpenWeatherMap API |
| `json` | Parses the weather API's JSON response |
| `anthropic` | Official SDK to talk to Claude |
| `client` | Your single connection to Claude — all requests go through this |

---

## Section 2 — The Three Tools

The agent has three tools. Every custom tool has **two parts**: a description (what Claude reads) and a function (what your computer runs).

### Tool 1 — `web_search` (built-in, Anthropic's servers)

```python
{
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 3,
}
```

- No Python function needed — Anthropic runs this on their servers
- Claude can search the internet up to 3 times per question
- Results come back automatically inside the response

---

### Tool 2 — `get_weather` (custom, calls OpenWeatherMap API)

**Part 1 — Description** (what Claude reads):

```python
WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Get the current real-time weather for any city...",
    "input_schema": {
        "properties": {
            "city":  {"type": "string"},   # required
            "units": {"type": "string", "enum": ["metric", "imperial"]}
        },
        "required": ["city"]
    }
}
```

Claude reads this to learn:
- The tool is called `get_weather`
- When to use it: when the user asks about weather
- What inputs to send: `city` (required), `units` (optional)

**Part 2 — Function** (your Python code):

```python
def run_get_weather(city: str, units: str = "metric") -> str:
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units={units}"
    data = json.loads(urllib.request.urlopen(url).read())
    return f"Weather in {city}: {data['main']['temp']}°C, {data['weather'][0]['description']}"
```

Claude **never sees this code**. It only sees the string you return.

---

### Tool 3 — `calculator` (custom, runs locally)

**Part 1 — Description:**

```python
CALCULATOR_TOOL = {
    "name": "calculator",
    "description": "Perform mathematical calculations...",
    "input_schema": {
        "properties": {
            "expression": {"type": "string"}  # e.g. "5000 * (1.08**10)"
        },
        "required": ["expression"]
    }
}
```

**Part 2 — Function:**

```python
def run_calculator(expression: str) -> str:
    result = eval(expression, {"math": math})
    return f"Result: {result}"
```

Claude sends `"5000 * (1.08**10)"`, your function evaluates it and returns `"Result: 10794.62"`.

---

### The Tool Registry — The Bridge Between Claude and Your Functions

```python
tools = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 3},
    CALCULATOR_TOOL,
    WEATHER_TOOL,
]

CUSTOM_TOOL_HANDLERS = {
    "calculator": run_calculator,
    "get_weather": run_get_weather,
}
```

`CUSTOM_TOOL_HANDLERS` is the **only connection** between Claude's world and your Python functions. When Claude says "call `get_weather`", your loop looks up `"get_weather"` in this dictionary and runs `run_get_weather()`.

---

## Section 3 — The Agent Loop

This is the heart of the file. It's a `while True` loop that keeps running until Claude says it's done.

```
START
  │
  ▼
Send question to Claude
  │
  ▼
Claude responds with stop_reason
  │
  ├── "end_turn"  → Claude is done → print answer → EXIT loop
  │
  └── "tool_use"  → Claude wants a tool
          │
          ├── Custom tool? → run YOUR Python function → send result back → LOOP AGAIN
          │
          └── Server tool? → result already in response → pass it forward → LOOP AGAIN
```

### Key lines explained

**Sending to Claude:**
```python
response = client.messages.create(
    model="claude-sonnet-4-6",  # which AI model to use
    max_tokens=4096,            # max response length
    tools=tools,                # what tools Claude can use
    messages=messages,          # full conversation history so far
)
```

**Checking why Claude stopped:**
```python
stop_reason = response.stop_reason
# "end_turn"  = Claude is done, has a final answer
# "tool_use"  = Claude wants to use a tool and is WAITING
```

**Running your custom tool:**
```python
handler = CUSTOM_TOOL_HANDLERS[block.name]  # look up the function
result  = handler(**block.input)            # run it with Claude's inputs
```

`block.input` is what Claude filled in — e.g. `{"city": "London", "units": "metric"}`.
The `**` unpacks it into `run_get_weather(city="London", units="metric")`.

**Sending the result back to Claude:**
```python
tool_results.append({
    "type": "tool_result",
    "tool_use_id": block.id,  # ties this result to Claude's original request
    "content": result,        # what your function returned
})
messages.append({"role": "user", "content": tool_results})
```

Claude receives this, reads the result, and loops again to write the final answer.

---

## How Claude and Your Functions Are Connected

This is the most important concept to understand.

Claude does **not** call your function directly. **You** call it. Claude just says *"I want to use this tool with these inputs"* and then **waits**. Your code reads that request, runs the function, and sends the result back.

Think of it like a **restaurant**:

```
Customer (Claude)       Waiter (your loop)       Kitchen (your function)
─────────────────       ──────────────────       ──────────────────────
"I want weather                               
 for Chennai"    ──►    reads the order   ──►    run_get_weather("Chennai")
                                                 calls OpenWeatherMap API
                                                 returns "34°C, Clear sky"
                 ◄──    serves the result ◄──   
reads the result,
writes final answer
```

### The exact timeline

```
YOUR CODE                          CLAUDE
──────────────────────────────────────────────────────────

1. You define WEATHER_TOOL ──────► Claude reads description
   (name, description,              Learns: tool exists,
    input_schema)                   what it does, what inputs needed

2. You send the question ────────► Claude thinks...
   client.messages.create(          "I need get_weather(city='Chennai')"
     tools=tools,                   
     messages=[question]            Stops and says:
   )                                stop_reason = "tool_use"
                                    block.name  = "get_weather"
                                    block.input = {"city": "Chennai"}

3. Your loop reads block ◄────────  (Claude is now WAITING)
   Runs run_get_weather("Chennai")
   Gets back "34°C, Clear sky"

4. You send result ──────────────► Claude reads "34°C, Clear sky"
   messages.append(tool_result)     Writes final answer
                                    stop_reason = "end_turn"

5. You print the answer ◄──────────
```

### Why this design?

| Claude's job | Your job |
|---|---|
| Decide **which** tool to call | Actually **run** the tool |
| Decide **what inputs** to pass | Handle the inputs and return a result |
| Read the result and **answer** | Send the result back to Claude |

Because your function could do **anything** — call an API, query a database, read a file, send an email — and Claude doesn't need to know the internals. This is why you can connect Claude to **any system in the world** just by writing a Python function and registering it in `CUSTOM_TOOL_HANDLERS`.

---

## Section 4 — Interactive Chat Loop

```python
while True:
    question = input("You: ").strip()   # wait for user to type
    if question.lower() in ("quit", "exit"):
        break
    ask_agent(question)                 # send to the agent
```

A simple loop that:
1. Waits for you to type something
2. Sends it to `ask_agent()`
3. Prints the answer
4. Repeats until you type `quit`

---

## Complete Flow — One Full Example

```
You type: "Is it warmer in Paris or Sydney? Show difference in Fahrenheit."
         ↓
Section 4 captures your input
         ↓
Section 3 sends it to Claude with the tools list
         ↓
Claude reads tool descriptions, decides:
  → call get_weather(city="Paris", units="imperial")
  → call get_weather(city="Sydney", units="imperial")
         ↓
Section 3 runs run_get_weather("Paris", "imperial")  → "70.34°F"
Section 3 runs run_get_weather("Sydney", "imperial") → "65.91°F"
         ↓
Results sent back to Claude
         ↓
Claude thinks: "I need the difference" 
  → calls calculator(expression="70.34 - 65.91")
         ↓
Section 3 runs run_calculator("70.34 - 65.91") → "Result: 4.43"
         ↓
Result sent back to Claude
         ↓
Claude writes final answer:
  "Paris is warmer by 4.43°F. Paris: 70.34°F, Sydney: 65.91°F"
         ↓
stop_reason = "end_turn" → answer printed
Section 4 waits for your next question
```

---

## Summary

| Component | File location | Purpose |
|---|---|---|
| `client` | Line 40 | Connection to Claude |
| `WEATHER_TOOL` | Lines 51–73 | Describes weather tool to Claude |
| `run_get_weather()` | Lines 75–125 | Actually fetches weather data |
| `CALCULATOR_TOOL` | Lines 137–156 | Describes calculator to Claude |
| `run_calculator()` | Lines 159–171 | Actually evaluates math |
| `tools` list | Lines 177–187 | All tools sent to Claude |
| `CUSTOM_TOOL_HANDLERS` | Lines 190–193 | Maps tool names to functions |
| `ask_agent()` | Lines 199–288 | The agent loop |
| `__main__` block | Lines 294–334 | Interactive chat interface |
