"""Markdown rendering for the agent's replies.

Replies are model output, so they're untrusted: anything in them that
looks like HTML must stay text, or it would become part of the page.
markdown-it-py with html disabled escapes it, and refuses unsafe link
targets such as javascript: URLs. Links open in a new tab.
"""

from markdown_it import MarkdownIt
from markupsafe import Markup

_md = (
    MarkdownIt("commonmark", {"html": False})
    .enable("table")
    .enable("strikethrough")
)


def _link_open(self, tokens, idx, options, env):
    tokens[idx].attrSet("target", "_blank")
    tokens[idx].attrSet("rel", "noopener noreferrer")
    return self.renderToken(tokens, idx, options, env)


_md.add_render_rule("link_open", _link_open)


def to_html(text: str) -> Markup:
    """Render Markdown to HTML that is safe to put in the page."""
    return Markup(_md.render(text))
