"""
Simple Agentic AI Example
--------------------------
This agent uses Claude as its "brain" and gives it a web search tool.
When you ask a question, Claude decides if it needs to search the web,
performs the search, reads the results, and gives you a final answer.

This is the core loop of agentic AI:
  1. Give Claude a goal
  2. Claude thinks and decides to use a tool
  3. The tool runs and returns a result
  4. Claude reads the result and thinks again
  5. Repeat until Claude has a final answer
"""

import os
import anthropic

# ---------------------------------------------------------------------------
# Step 1: Create the AI client
# This is our connection to Claude (the "brain")
# It reads your API key from the ANTHROPIC_API_KEY environment variable
# ---------------------------------------------------------------------------
client = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# Step 2: Define the tools Claude can use
# Tools are things Claude is ALLOWED to do — like searching the web.
# We describe what the tool does, and Claude decides WHEN to use it.
# ---------------------------------------------------------------------------
tools = [
    {
        # This is a built-in Anthropic tool — we don't write the search code.
        # Anthropic runs this tool on their servers for us.
        "type": "web_search_20260209",  # the type tells Anthropic which tool to use
        "name": "web_search",           # the name Claude uses to call the tool
        "max_uses": 3,                  # limit: Claude can search at most 3 times per question
    }
]

# ---------------------------------------------------------------------------
# Step 3: The Agent Loop
# This function sends a question to Claude and loops until it's done.
# ---------------------------------------------------------------------------
def ask_agent(question: str) -> str:
    """
    Send a question to the agent and get a final answer.

    The agent will:
    - Think about the question
    - Optionally search the web for current information
    - Return a clear, researched answer
    """
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    # This is the conversation history.
    # We start with just the user's question.
    messages = [
        {"role": "user", "content": question}
    ]

    # Keep looping until Claude says it's done (stop_reason = "end_turn")
    while True:
        print("\n[Agent is thinking...]")

        # Send the conversation to Claude
        response = client.messages.create(
            model="claude-opus-5-5",     # the AI model we're using
            max_tokens=4096,             # max length of the response
            tools=tools,                 # the tools Claude can use
            messages=messages,           # the full conversation so far
        )

        # Check WHY Claude stopped generating text
        stop_reason = response.stop_reason

        if stop_reason == "end_turn":
            # Claude is done! Extract the final text answer.
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n[Final Answer]\n{block.text}")
                    return block.text

        elif stop_reason == "tool_use":
            # Claude wants to use a tool (e.g., web search).
            # We need to:
            #   1. Find which tool Claude wants to use
            #   2. The tool runs automatically on Anthropic's servers
            #   3. Add the results back to the conversation
            #   4. Loop again so Claude can read the results

            print("\n[Agent is searching the web...]")

            # Add Claude's response (including its tool request) to history
            messages.append({"role": "assistant", "content": response.content})

            # Find the tool use block in the response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → Searching for: {block.input.get('query', '')}")

                # If this is a web search result block, capture it
                if block.type == "web_search_tool_result":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                    })

            # If the server already embedded tool results in the response,
            # add them to the conversation so Claude can read them next turn.
            # (For server-side tools like web_search, results come back
            #  in the same response — we just need to pass them forward.)
            if not tool_results:
                # Server tools return results inline — pass the full response content
                messages.append({"role": "user", "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search completed. Results are in the previous message.",
                    }
                    for block in response.content if block.type == "tool_use"
                ]})
            else:
                messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason
            print(f"[Unexpected stop reason: {stop_reason}]")
            break

    return "Agent could not produce an answer."


# ---------------------------------------------------------------------------
# Step 4: Run the agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Check that an API key is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set your ANTHROPIC_API_KEY environment variable.")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)

    # Try a few example questions
    questions = [
        "What is the latest version of Python as of today?",
        "What are the top 3 AI models released in 2025?",
    ]

    for question in questions:
        ask_agent(question)
        print("\n")
