# Architecture

basic-ui is a pip-installable Flask chat interface for Basic Bot agents.
It receives a `BotRuntime` from the engine and wraps it in routes.

## Files

| File | What it does |
|------|--------------|
| `server.py` | `create_local_app(agent_path)` — calls the engine factory, builds Flask routes for chat, history, models, and health. |
| `templates/index.html` | Jinja2 template. Agent name injected via `{{ agent_name }}`. Markdown rendered client-side by marked.js. |
| `static/css/styles.css` | Dark-mode styles, system font stack, responsive layout. |
| `static/js/chat.js` | Single file, no modules, no auth. Handles message send/receive, model selection, history loading, markdown rendering. |

## Design Decisions

**No dependency on basic-bot at the package level.** basic-ui imports
from `basic_bot` at runtime, but does not declare it in `pyproject.toml`.
The agent repo depends on both and wires them together. This avoids
circular version pinning — basic-ui and basic-bot can version
independently.

**Server-side rendering is not used.** The engine returns raw text;
marked.js converts markdown to HTML in the browser. This matches the
engine's design: rendering is a UI concern, not an engine concern.

**`agent_name` comes from `dashboard.json`.** The factory loads the
dashboard and stores it on the runtime. The server reads
`runtime.dashboard["name"]` and passes it to the template. No
hardcoded agent names.

**Templates and static files ship inside the package.** `pyproject.toml`
declares them as package data so pip includes them in the install. The
server resolves paths via `Path(__file__).parent`, which works whether
the package is installed normally or editable.
