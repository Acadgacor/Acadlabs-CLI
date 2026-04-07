"""
Acadlabs CLI - Main Entry Point

AI-powered coding assistant CLI dengan Agentic Loop.
"""
import typer

from acadlabs_cli.commands import auth_app, chat_app, config_app

# Main app
app = typer.Typer(
    name="acadlabs",
    help="AI-powered coding assistant CLI",
    add_completion=True
)

# Register sub-commands from modules
app.add_typer(auth_app, name="auth")
app.add_typer(chat_app, name="chat")
app.add_typer(config_app, name="config")

# Quick access commands (backward compatibility)
# These are shortcuts that call the sub-command versions
from acadlabs_cli.commands.auth import login, login_google
from acadlabs_cli.commands.chat import start as chat_start

app.command(name="login")(login)
app.command(name="login-google")(login_google)
app.command(name="chat")(chat_start)


if __name__ == "__main__":
    app()