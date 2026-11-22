"""The web page for a Bountiful agent.

Flask routes over basic_bot.session. Each request returns HTML that
the page puts in place, so the browser keeps nothing of its own.
"""

import json
import logging
import os
import queue
import signal
import threading

from flask import Flask, Response, abort, render_template, request
from werkzeug.exceptions import HTTPException

import basic_ui.config as ui_config
from basic_bot.session import SessionBusy, SessionError
from basic_ui.render import to_html

logger = logging.getLogger(__name__)

HOST_NAMES = {"local": "Local", "api": "API"}

LOCAL_NAMES = ("localhost", "127.0.0.1")

PING_SECONDS = 15

PAGE_HEADER = "X-Basic-UI"

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
    app.config["TRUSTED_HOSTS"] = list(LOCAL_NAMES)

    @app.before_request
    def same_origin_only():
        """Refuse a POST that didn't come from the page itself."""
        if request.method != "POST":
            return None
        if request.headers.get(PAGE_HEADER) != "1":
            logger.warning("Refused a request without the page's header")
            abort(403)
        origin = request.headers.get("Origin")
        allowed = {f"http://{name}:{ui_config.FLASK_PORT}" for name in LOCAL_NAMES}
        if origin is not None and origin not in allowed:
            logger.warning("Refused a request from %s", origin)
            abort(403)
        return None

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = CSP
        return response

    @app.errorhandler(Exception)
    def unexpected_error(e):
        """Show an unexpected failure in the conversation.

        A request from the page gets the error as a message, and the
        message box back. Anything else gets plain text.
        """
        if isinstance(e, HTTPException):
            return e
        logger.exception("Unexpected error on %s %s", request.method, request.path)
        if request.headers.get(PAGE_HEADER) != "1":
            return "Something went wrong. The terminal shows the details.", 500
        return render_template("partials/unexpected_error.html"), 500

    @app.context_processor
    def shared():
        return {"agent_name": session.name, "host_names": HOST_NAMES}


    @app.get("/")
    def index():
        history = session.history()
        return render_template(
            "index.html",
            controls=session.controls(),
            history=[_view(m) for m in history],
            notice=_history_notice(history),
        )

    @app.get("/favicon.ico")
    def favicon():
        return app.send_static_file("favicon.ico")


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
            updated = session.update_memory()
        except SessionError as e:
            return render_template("partials/memory_done.html", error=str(e))
        if not updated:
            return render_template(
                "partials/memory_done.html",
                error="Memory couldn't be updated this time. "
                      "It will try again before the next reply.",
            )
        return render_template("partials/memory_done.html", error=None)


    @app.get("/events")
    def events():
        listener = session.events.listen()

        def stream():
            try:
                yield ": connected\n\n"
                while True:
                    try:
                        event = listener.get(timeout=PING_SECONDS)
                    except queue.Empty:
                        yield ": ping\n\n"
                        continue
                    yield f"event: {event['kind']}\ndata: {json.dumps(event)}\n\n"
            finally:
                session.events.stop_listening(listener)

        return Response(
            stream(), mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )


    @app.post("/interrupt")
    def interrupt():
        session.interrupt()
        return "", 204

    @app.post("/end")
    def end():
        threading.Timer(0.5, os.kill, (os.getpid(), signal.SIGINT)).start()
        return render_template("partials/session_ended.html")


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
