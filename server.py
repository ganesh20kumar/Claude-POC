"""
Web server wrapper for agent.py.

Serves the chat UI and exposes a /chat endpoint that runs the real agent.

Usage:
  pip install flask
  python server.py

Then open http://localhost:5000 in your browser.
"""

import json
import os
from flask import Flask, request, jsonify, send_from_directory

import agent as ag

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    ALLOWED_MODELS = {
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "claude-sonnet-5-5",
        "claude-opus-5-5",
    }
    model = data.get("model", "claude-sonnet-4-6")
    if model not in ALLOWED_MODELS:
        model = "claude-sonnet-4-6"

    collected: list[dict] = []

    # Haiku 4.5 only supports the basic web_search variant
    if model == "claude-haiku-4-5":
        web_search_tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}
    else:
        web_search_tool = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}
    model_tools = [web_search_tool] + [t for t in ag.tools if t.get("name") not in ("web_search",)]

    original_ask = ag.ask_agent

    def instrumented_ask(q: str) -> str:
        messages = [{"role": "user", "content": q}]
        while True:
            response = ag.client.messages.create(
                model=model,
                max_tokens=8192,
                tools=model_tools,
                messages=messages,
            )
            stop_reason = response.stop_reason

            # Fix: collect ALL text blocks; also handle max_tokens gracefully
            if stop_reason in ("end_turn", "max_tokens"):
                texts = [b.text for b in response.content if hasattr(b, "text")]
                for t in texts:
                    collected.append({"type": "text", "text": t})
                return texts[-1] if texts else ""

            elif stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                custom_tool_results = []
                has_server_tool = False

                for block in response.content:
                    # Fix: collect any preamble text ("I'll search for…") that
                    # arrives alongside a tool_use stop — previously silently dropped.
                    if hasattr(block, "text"):
                        collected.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use" and block.name in ag.CUSTOM_TOOL_HANDLERS:
                        handler = ag.CUSTOM_TOOL_HANDLERS[block.name]
                        result = handler(**block.input)
                        collected.append({
                            "type": "tool",
                            "tool": block.name,
                            "input": json.dumps(block.input),
                            "output": result,
                        })
                        custom_tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                    elif block.type == "web_search_tool_result":
                        # Server-side tool: result already lives in the assistant
                        # message — no separate user tool_result message needed.
                        has_server_tool = True
                        collected.append({
                            "type": "tool",
                            "tool": "web_search",
                            "input": "web_search(...)",
                            "output": "Web search results received.",
                        })

                if custom_tool_results:
                    messages.append({"role": "user", "content": custom_tool_results})
                elif not has_server_tool:
                    # Unknown tool_use block — send a placeholder result so the
                    # loop can continue rather than sending an empty user message.
                    fallback = [
                        {"type": "tool_result", "tool_use_id": b.id,
                         "content": "Done."}
                        for b in response.content if b.type == "tool_use"
                    ]
                    if fallback:
                        messages.append({"role": "user", "content": fallback})
                # For server tools (web_search), the result is already embedded in
                # the assistant content; just loop and call the API again.
            else:
                break

        return "Agent could not produce an answer."

    try:
        instrumented_ask(question)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"parts": collected})


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY before starting the server.")
        raise SystemExit(1)
    print("Starting Agent Chat server at http://localhost:5000")
    app.run(debug=False, port=5000)
