"""UI defaults.

Plain constants for the web front end. Every value here can be
overridden by adding the same name (any case) to the agent's
config.toml. The override is applied by apply_overrides() at startup.

Consumers must use `import basic_ui.config as ui_config` and then
`ui_config.X`, never `from basic_ui.config import X`.
"""

FLASK_PORT = 11777
HOST = "127.0.0.1"

DEBUG = False


def apply_overrides(overrides: dict) -> None:
    """Override defaults from the agent's config.toml."""
    constants = globals()
    for key, value in overrides.items():
        upper_key = key.upper()
        if upper_key in constants:
            constants[upper_key] = value
