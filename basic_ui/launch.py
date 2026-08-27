"""Launch a Basic Bot agent locally.

Orchestrates: secrets from keyring, embedding server, inference
server (always, for summary), Flask UI, and teardown on exit.
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
    """Full local launch: secrets, servers, Flask UI."""
    agent_path = Path(agent_path)

    from basic_bot.secrets_env import load as load_secrets
    load_secrets(agent_path)

    config = _read_config(agent_path)
    flask_port = config["flask_port"]

    from basic_bot.config import EMBEDDING_PROVIDER, EMBEDDING_URL, INFERENCE_URL
    from basic_bot.infrastructure.server import ensure_embedding, ensure_inference, stop

    llama_embed = ensure_embedding(EMBEDDING_URL) if EMBEDDING_PROVIDER == "local" else None

    # Inference server is permanent infrastructure — summary always
    # runs locally regardless of chat provider selection.
    summary_model = config.get("summary_model") or "qwen3-8b-q4_k_m"
    llama_infer = ensure_inference(summary_model, INFERENCE_URL)

    try:
        from basic_ui.server import create_local_app
        app = create_local_app(agent_path)
        app.run(port=flask_port, debug=True, use_reloader=False)
    finally:
        if llama_embed is not None:
            stop(llama_embed)
        if llama_infer is not None:
            stop(llama_infer)
