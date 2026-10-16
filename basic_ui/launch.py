"""Launch a Bountiful agent's web front end.

Called by bountiful's run.py shim. Opens the agent's session, starts
its default model, and serves the web page until Ctrl-C or the
terminal window closes. The session does all engine work, including
shutdown: everything happens inside `with session`, on the main
thread, so every way of stopping ends in session.close().

config.toml is read once, by the session. The session applies the
engine's overrides as it opens; this module then applies the UI's
from the same settings.
"""

import logging
import sys
from pathlib import Path

import basic_ui.config as ui_config
from basic_bot.session import Session, SessionError
from basic_ui.app import create_app

logger = logging.getLogger(__name__)


def launch(agent_path: Path) -> None:
    """Open the session, start the model, and serve the page."""
    try:
        session = Session.open(agent_path, log_to_terminal=True)
    except SessionError as e:
        sys.exit(f"ERROR: {e}")

    # The session applied the engine's overrides; these are the UI's
    ui_config.apply_overrides(session.agent_config)

    with session:
        try:
            session.start()
        except SessionError as e:
            sys.exit(f"ERROR: {e}")

        app = create_app(session)
        logger.info(
            "Starting the web page at http://localhost:%d",
            ui_config.FLASK_PORT,
        )
        app.run(
            host=ui_config.HOST,
            port=ui_config.FLASK_PORT,
            debug=ui_config.DEBUG,
            use_reloader=False,
        )
