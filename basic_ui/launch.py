"""Launch a Bountiful agent locally.

Orchestrates the full lifecycle: loads secrets, starts the chat
server, builds the runtime, starts Flask, and tears everything
down on exit.

This is the single entry point called by bountiful's run.py shim.
Engine work is delegated to basic-bot. The Flask app is delegated
to basic-ui's app module. This module sequences them.
"""

from pathlib import Path


def launch(agent_path: Path) -> None:
    """Full local launch: secrets, servers, runtime, Flask UI."""
    agent_path = Path(agent_path)

    from basic_bot.secrets_env import load as load_secrets
    from basic_bot.infrastructure.server import start, stop_all, CHAT
    from basic_bot.factory import create_runtime

    load_secrets(agent_path)
    start(CHAT)
    runtime = create_runtime(agent_path)

    try:
        from basic_ui.app import create_local_app
        app = create_local_app(runtime)
        app.run(port=11777, debug=True, use_reloader=False)
    finally:
        print("\nShutting down")
        stop_all()
