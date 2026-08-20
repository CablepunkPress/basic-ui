"""Launch a Basic Bot agent locally.

Orchestrates: secrets from keyring, llama-server if needed,
Flask UI, and teardown on exit.
"""

import json
from pathlib import Path

from basic_bot.config import EMBEDDING_PROVIDER, EMBEDDING_URL
from basic_bot.secrets_env import load as load_secrets
from basic_bot.infra.server import ensure, stop
from basic_ui.server import create_local_app

DEFAULT_FLASK_PORT = 11555


def _read_config(agent_path: Path) -> dict:
    """Read config.json, falling back to defaults for missing fields."""
    config_path = agent_path / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def launch(agent_path: Path) -> None:
    """Full local launch: secrets, llama-server, Flask UI."""
    agent_path = Path(agent_path)

    load_secrets(agent_path)

    config = _read_config(agent_path)
    flask_port = config.get("flask_port", DEFAULT_FLASK_PORT)

    llama = ensure(EMBEDDING_URL) if EMBEDDING_PROVIDER == "local" else None

    try:
        app = create_local_app(agent_path)
        app.run(port=flask_port, debug=True, use_reloader=False)
    finally:
        if llama is not None:
            stop(llama)
