"""Launch a Bountiful agent locally.

Orchestrates the full lifecycle: loads secrets, applies config
overrides, builds the runtime, starts the default model, starts
Flask, and tears everything down on exit.

This is the single entry point called by bountiful's run.py shim.
Engine work is delegated to basic-bot. The Flask app is delegated
to basic-ui's app module. This module sequences them.
"""

import logging
import sys
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)


def _read_config(agent_path: Path) -> dict:
    """Read config.toml from the agent directory."""
    config_path = agent_path / "config.toml"
    if config_path.exists():
        return tomllib.loads(config_path.read_text())
    return {}


def launch(agent_path: Path) -> None:
    """Full local launch: overrides, secrets, runtime, model, Flask UI."""
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
    from basic_bot.infrastructure.server import ServerError, stop_all
    from basic_bot.factory import create_runtime

    load_secrets(agent_path)

    runtime = create_runtime(agent_path)

    try:
        # Start the agent's default model. A local default starts its
        # server; an API default starts nothing.
        try:
            registry = runtime.chat_provider
            registry.select(registry.get_default_model())
        except ServerError as e:
            sys.exit(f"\nERROR: {e}")

        import basic_ui.config as ui_config
        from basic_ui.app import create_local_app

        app = create_local_app(runtime)
        app.run(
            port=ui_config.FLASK_PORT,
            debug=ui_config.DEBUG,
            use_reloader=ui_config.USE_RELOADER,
        )
    finally:
        print()
        logger.info("Shutting down")
        logger.info("Flask server stopped")
        stop_all()
