"""Launch a Bountiful agent's web front end.

Called with an open session. Starts its default model and serves the
web page until Ctrl-C or the terminal window closes. Whoever opened
the session closes it, in a `with` block on the main thread, so every
way of stopping ends in session.close().

config.toml is read once, by the session. The session applied the
harness's overrides as it opened; this module applies the UI's from
the same settings.
"""

import logging
import sys

import basic_ui.config as ui_config
from basic_bot.session import Session, SessionError
from basic_ui.app import create_app

logger = logging.getLogger(__name__)


def launch(session: Session) -> None:
    """Start the model and serve the page."""
    ui_config.apply_overrides(session.agent_config)

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
        host="127.0.0.1",
        port=ui_config.FLASK_PORT,
        debug=ui_config.DEBUG,
        use_reloader=False,
    )
