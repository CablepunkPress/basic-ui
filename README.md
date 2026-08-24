# Basic UI

Reference Flask chat interface for [Basic Bot](https://github.com/CablepunkPress/basic-bot) agents.

This is a **pip dependency**, not a standalone application. Agents
install it alongside the engine and call it from their `run.py`.

**To create and run your own agent, start at
[build-a-bot](https://github.com/CablepunkPress/build-a-bot).**

## What It Provides

- Full local launch orchestration: secrets, llama-server, Flask, teardown
- Dark-mode chat interface with markdown rendering (via marked.js)
- Model selector sorted by rank, with per-model effort levels and Deep Reasoning toggle
- Conversation history loaded at startup
- Agent name displayed from dashboard.json

## Usage

An agent's `run.py` shim calls:

```python
from basic_ui.launch import launch

launch("/path/to/agent")
```

`launch()` loads API keys from the keyring, starts llama-server for
embeddings if needed, creates the Flask app via the engine's
`create_runtime()`, runs it, and tears down on Ctrl+C.

## Installing as a Dependency

Agents declare this in their `pyproject.toml`:

```toml
"basic-ui @ git+https://github.com/CablepunkPress/basic-ui.git@main"
```

Flask is included as a dependency of this package. The engine does
not depend on basic-ui, and basic-ui does not depend on the engine
at the package level — the agent repo wires them together.

## License

MIT
