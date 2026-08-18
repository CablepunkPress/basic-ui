# Basic UI

Reference Flask chat interface for [Basic Bot](https://github.com/CablepunkPress/basic-bot) agents.

This is a **pip dependency**, not a standalone application. Agents
install it alongside the engine and call it from their `run.py`.

**To create and run your own agent, start at
[build-a-bot](https://github.com/CablepunkPress/build-a-bot).**

## What It Provides

- Dark-mode chat interface with markdown rendering (via marked.js)
- Model selector with per-model effort levels and Deep Reasoning toggle
- Conversation history loaded at startup
- Agent name displayed from dashboard.json

## Usage

An agent's `run.py` calls:

```python
from basic_ui.server import create_local_app

app = create_local_app("/path/to/agent")
app.run(port=11555)
```

`create_local_app` calls the engine's `create_runtime()` internally,
then wraps the result in Flask routes. The agent directory provides
the identity, persona, and tools; basic-ui provides the interface.

## Installing as a Dependency

Agents declare this in their `pyproject.toml`:

```toml
"basic-ui @ git+https://github.com/CablepunkPress/basic-ui.git@v0.2.0"
```

Flask is included as a dependency of this package. The engine does
not depend on basic-ui, and basic-ui does not depend on the engine
at the package level — the agent repo wires them together.

## License

MIT
