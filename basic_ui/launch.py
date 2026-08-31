"""Launch a Bountiful agent locally.

Orchestrates: secrets from keyring (if configured), chat server,
Flask UI, and teardown on exit.

Embedding and summary servers start on demand during fold.
"""

import tomllib
from pathlib import Path


def _read_config(agent_path: Path) -> dict:
    """Read config.toml from the agent directory."""
    config_path = agent_path / "config.toml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"No config.toml found in {agent_path}. Run 'python build.py' first."
        )
    return tomllib.loads(config_path.read_text())


def launch(agent_path: Path) -> None:
    """Full local launch: secrets, chat server, Flask UI."""
    agent_path = Path(agent_path)

    from basic_bot.secrets_env import load as load_secrets
    load_secrets(agent_path)

    config = _read_config(agent_path)
    flask_port = config.get("flask_port", 11777)

    from basic_bot.infrastructure.server import start, stop_all, CHAT

    start(CHAT)

    try:
        from basic_ui.app import create_local_app
        app = create_local_app(agent_path)
        app.run(port=flask_port, debug=True, use_reloader=False)
    finally:
        print("\nShutting down")
        stop_all()
