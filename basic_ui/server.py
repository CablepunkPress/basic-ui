"""Generic local Flask server for a Basic Bot agent.

Single user, no auth. Serves the chat UI and talks directly to the
engine. The agent is defined entirely by its directory — persona.md,
dashboard.json, and optional tools/.
"""

import asyncio
import logging
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from basic_bot.chat import chat_with_model
from basic_bot.config import (
    FOLD_MODE,
    HISTORY_LIMIT,
    WINDOW_CEILING,
)
from basic_bot.factory import create_runtime
from basic_bot.fold import build_metadata, fold_rag, fold_summary, should_fold
from basic_bot.memory import get_messages

logger = logging.getLogger(__name__)

DEFAULT_USER = "local"


def create_local_app(agent_path: str | Path) -> Flask:
    """Build a Flask app for the agent at the given directory."""

    runtime = create_runtime(agent_path)

    ui_dir = Path(__file__).parent
    app = Flask(
        __name__,
        template_folder=str(ui_dir / "templates"),
        static_folder=str(ui_dir / "static"),
    )

    logger.info("=" * 50)
    logger.info("%s starting locally", runtime.agent_id)
    logger.info("Default model: %s", runtime.chat_provider.get_default_model())
    logger.info(
        "Tools: %d [%s]",
        len(runtime.tool_registry),
        ", ".join(runtime.tool_registry.keys()) or "none",
    )
    logger.info("=" * 50)

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            agent_name=runtime.dashboard.get("name", "Basic Bot"),
        )

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Message is required"}), 400

        model_id = data.get("model", runtime.chat_provider.get_default_model())
        effort = data.get("effort")
        thinking = data.get("thinking", False)
        user_id = DEFAULT_USER

        logger.info("Chat — model: %s (%d chars)", model_id, len(message))

        try:
            result = asyncio.run(
                chat_with_model(
                    runtime, user_id, message, model_id, effort, thinking,
                )
            )
        except Exception as e:
            logger.exception("Chat error: %s", str(e))
            return jsonify({"error": "Internal server error"}), 500

        metadata = build_metadata(result)
        seq = runtime.store.save_turn(
            user_id, message, result["reply"], metadata=metadata,
        )
        logger.info("Saved turn (seq %d–%d)", seq, seq + 1)

        fold_state = should_fold(runtime.store, user_id)
        if fold_state:
            chunk = fold_rag(runtime.store, user_id, fold_state)
            if chunk:
                if FOLD_MODE == "sync":
                    logger.info("Fold triggered — RAG done, summarizing (sync)")
                    fold_summary(
                        runtime.summary_provider, runtime.store,
                        user_id, fold_state["summary"], chunk,
                    )
                else:
                    thread = threading.Thread(
                        target=fold_summary,
                        args=(
                            runtime.summary_provider, runtime.store,
                            user_id, fold_state["summary"], chunk,
                        ),
                        daemon=True,
                    )
                    thread.start()
                    logger.info("Fold triggered — RAG done, summary in background")

        return jsonify({
            "response": result["reply"],
            "seq": seq,
            "model_used": result["model_used"],
            "display_name": result["display_name"],
            "effort": result["effort"],
            "thinking": result["thinking"],
            "fallback": result["fallback"],
        })

    @app.route("/history", methods=["GET"])
    def history():
        user_id = DEFAULT_USER

        limit_param = request.args.get("limit")
        if limit_param:
            try:
                limit = min(int(limit_param), WINDOW_CEILING)
            except ValueError:
                limit = HISTORY_LIMIT
        else:
            limit = HISTORY_LIMIT

        messages = get_messages(runtime.store, user_id, limit)

        return jsonify({
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "seq": msg["seq"],
                    "metadata": msg.get("metadata"),
                }
                for msg in messages
            ],
            "count": len(messages),
        })

    @app.route("/models", methods=["GET"])
    def models_endpoint():
        models = runtime.chat_provider.get_models()
        return jsonify({
            "models": {
                mid: {
                    "display_name": m.display_name,
                    "effort_levels": m.effort_levels,
                    "thinking_type": m.thinking_type,
                    "rank": m.rank,
                }
                for mid, m in models.items()
            },
            "default": runtime.chat_provider.get_default_model(),
        })

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "agent": runtime.agent_id})

    return app
