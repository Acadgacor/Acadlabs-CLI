"""Commands module - CLI commands for Acadlabs"""

from acadlabs_cli.commands.auth import app as auth_app
from acadlabs_cli.commands.chat import app as chat_app
from acadlabs_cli.commands.config import app as config_app

__all__ = [
    "auth_app",
    "chat_app",
    "config_app",
]
