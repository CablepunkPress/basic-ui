"""Web front end for a Bountiful agent.

Flask routes over basic_bot.session, rendered as HTML with HTMX. The
browser holds no state: the session holds the settings and the
conversation, and every request returns the HTML to show.

A message moves through three requests, so each step appears as soon
as it's ready:

    POST /message   shows the user's message and "Thinking…"
    POST /reply     replaces "Thinking…" with the reply, then shows
                    "Updating memory…" when the reply says one is due
    POST /memory    runs the update and removes the notice

The message box stays disabled until the last step finishes. Each
response says whether to re-enable it, so the server, not the browser,
decides when the next message can be sent.
"""

import logging

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from basic_bot.session import SessionBusy, SessionError
from basic_ui.render import to_html

logger = logging.getLogger(__name__)

HOST_NAMES = {"local": "Local", "api": "API"}

# The page loads nothing from anywhere else, runs no inline script,
# and can't be framed. HTMX's requests go back to this server only.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'"
)


def _badge(meta: dict | None) -> str:
    """Model, effort, Deep Reasoning, and fallback, as shown under a reply."""
    if not meta:
        return ""
    parts = []
    if meta.get("display_name"):
        parts.append(meta["display_name"])
    if meta.get("effort"):
        parts.append(meta["effort"].capitalize())
    if meta.get("thinking"):
        parts.append("Deep Reasoning")
    if meta.get("fallback"):
        parts.append("Fallback")
    return " · ".join(parts)


def _view(message: dict) -> dict:
    """A stored message, ready for the template."""
    if message["role"] == "user":
        return {"role": "user", "seq": message["seq"], "text": message["content"]}
    return {
        "role": "assistant",
        "seq": message["seq"],
        "html": to_html(message["content"]),
        "badge": _badge(message.get("metadata")),
    }


def _history_notice(history: list[dict]) -> str:
    if not history:
        return "No messages yet."
    return (
        f"Last {len(history)} messages loaded: "
        f"#{history[0]['seq']}–#{history[-1]['seq']}"
    )


def create_app(session) -> Flask:
    """Build the web app over an open, started session."""
    app = Flask(__name__)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = CSP
        return response

    @app.errorhandler(Exception)
    def unexpected_error(e):
        """Show an unexpected failure as a system message.

        htmx 4 swaps error responses into the page, so a request from
        htmx gets a fragment, redirected into the conversation: the
        error is added, any "Thinking…" or "Updating memory…" notice is
        removed, and the message box is enabled again. Anything else,
        like the page itself failing to load, gets plain text. Ordinary
        HTTP errors, like a missing file, pass through unchanged.
        """
        if isinstance(e, HTTPException):
            return e
        logger.exception("Unexpected error on %s %s", request.method, request.path)
        if "HX-Request-Type" not in request.headers:
            return "Something went wrong. The terminal shows the details.", 500
        return (
            render_template("partials/unexpected_error.html"),
            500,
            {"HX-Retarget": "#messages", "HX-Reswap": "beforeend"},
        )

    @app.context_processor
    def shared():
        return {"agent_name": session.name, "host_names": HOST_NAMES}

    # --- The page ---

    @app.get("/")
    def index():
        history = session.history()
        return render_template(
            "index.html",
            controls=session.controls(),
            history=[_view(m) for m in history],
            notice=_history_notice(history),
        )

    # --- A message, in three steps ---

    @app.post("/message")
    def message():
        text = request.form.get("message", "").strip()
        if not text:
            return "", 204
        return render_template("partials/message_sent.html", text=text)

    @app.post("/reply")
    def reply():
        text = request.form.get("message", "")
        try:
            r = session.send(text)
        except SessionBusy as e:
            return render_template("partials/reply_failed.html", text=text, error=str(e))
        except SessionError as e:
            return render_template("partials/reply_failed.html", text=text, error=str(e))

        user = {"role": "user", "seq": r.seq, "text": text}
        assistant = {
            "role": "assistant",
            "seq": r.seq + 1,
            "html": to_html(r.text),
            "badge": _badge({
                "display_name": r.display_name,
                "effort": r.effort,
                "thinking": r.thinking,
                "fallback": r.fallback,
            }),
        }
        return render_template(
            "partials/reply.html",
            user=user,
            assistant=assistant,
            update_due=r.memory_update_due,
        )

    @app.post("/memory")
    def memory():
        try:
            session.update_memory()
        except SessionError as e:
            return render_template("partials/memory_done.html", error=str(e))
        return render_template("partials/memory_done.html", error=None)

    # --- Settings, from the drawer ---

    def _drawer(notice: str | None = None, error: str | None = None):
        return render_template(
            "partials/drawer.html",
            controls=session.controls(),
            notice=notice,
            error=error,
        )

    @app.post("/settings/host")
    def set_host():
        try:
            session.select_host(request.form.get("host", ""))
        except SessionError as e:
            return _drawer(error=str(e))
        return _drawer(notice=f"Now running {session.controls().model.display_name}.")

    @app.post("/settings/model")
    def set_model():
        try:
            session.select_model(request.form.get("model_id", ""))
        except SessionError as e:
            return _drawer(error=str(e))
        return _drawer(notice=f"Now running {session.controls().model.display_name}.")

    @app.post("/settings/effort")
    def set_effort():
        try:
            session.set_effort(request.form.get("level", ""))
        except SessionError as e:
            return _drawer(error=str(e))
        return _drawer(notice=f"Effort set to {session.controls().effort}.")

    @app.post("/settings/reasoning")
    def set_reasoning():
        on = request.form.get("on") == "true"
        try:
            session.set_reasoning(on)
        except SessionError as e:
            return _drawer(error=str(e))
        return _drawer(notice=f"Deep Reasoning turned {'on' if on else 'off'}.")

    return app
