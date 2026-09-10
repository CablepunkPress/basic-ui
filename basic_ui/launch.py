"""Launch a Bountiful agent locally.

Orchestrates the full lifecycle: loads secrets, applies config
overrides, starts the chat server, builds the runtime, starts
Flask, and tears everything down on exit.

This is the single entry point called by bountiful's run.py shim.
Engine work is delegated to basic-bot. The Flask app is delegated
to basic-ui's app module. This module sequences them.
"""

import tomllib
from pathlib import Path


def _read_config(agent_path: Path) -> dict:
    """Read config.toml from the agent directory."""
    config_path = agent_path / "config.toml"
    if config_path.exists():
        return tomllib.loads(config_path.read_text())
    return {}


def launch(agent_path: Path) -> None:
    """Full local launch: overrides, secrets, servers, runtime, Flask UI."""
    agent_path = Path(agent_path)

    # Read config.toml and apply overrides FIRST — before any other
    # imports read from config modules
    config_toml = _read_config(agent_path)

    from basic_bot.config import apply_overrides as apply_bot_overrides
    from basic_ui.config import apply_overrides as apply_ui_overrides

    apply_bot_overrides(config_toml)
    apply_ui_overrides(config_toml)

    # Now proceed — all config values reflect any user overrides
    from basic_bot.secrets_env import load as load_secrets
    from basic_bot.infrastructure.server import start, stop_all, CHAT
    from basic_bot.factory import create_runtime

    load_secrets(agent_path)
    
    # Only start the chat server if not configured for API-first
    provider = config_toml.get("inference_provider", "local")
    if provider != "claude":
        start(CHAT)

    runtime = create_runtime(agent_path)

    try:
        import basic_ui.config as ui_config
        from basic_ui.app import create_local_app

        app = create_local_app(runtime)
        app.run(
            port=ui_config.FLASK_PORT,
            debug=ui_config.DEBUG,
            use_reloader=ui_config.USE_RELOADER,
        )
    finally:
        print("\nShutting down")
        stop_all()
