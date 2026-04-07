"""Config commands"""
import json
from pathlib import Path
import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console()
app = typer.Typer(name="config", help="Configuration commands")

CONFIG_DIR = Path.home() / ".acadlabs"
CONFIG_FILE = CONFIG_DIR / "config.json"


@app.command()
def init():
    """Initialize config file with API keys"""
    console.print("[bold blue]Acadlabs CLI Configuration[/bold blue]\n")

    # Check if config already exists
    if CONFIG_FILE.exists():
        overwrite = Prompt.ask("Config already exists. Overwrite?", choices=["y", "n"], default="n")
        if overwrite.lower() != "y":
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Prompt for values
    openrouter_key = Prompt.ask("OpenRouter API Key (leave empty if using Supabase Edge Function)", default="")
    supabase_url = Prompt.ask("Supabase URL (e.g., https://xxx.supabase.co)")
    supabase_key = Prompt.ask("Supabase Anon Key", password=True)
    default_model = Prompt.ask("Default Model", default="anthropic/claude-3.5-sonnet")

    # Save config
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = {
        "openrouter_api_key": openrouter_key,
        "supabase_url": supabase_url,
        "supabase_key": supabase_key,
        "default_model": default_model
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"\n[green]Config saved to {CONFIG_FILE}[/green]")


@app.command()
def show():
    """Show current config (keys are masked)"""
    if not CONFIG_FILE.exists():
        console.print("[red]Config not found. Run 'acadlabs config init' first.[/red]")
        return

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    console.print("\n[bold cyan]Current Configuration:[/bold cyan]")
    console.print(f"  Supabase URL: {config.get('supabase_url', 'N/A')}")
    console.print(f"  OpenRouter Key: {config.get('openrouter_api_key', 'N/A')[:10]}...")
    console.print(f"  Supabase Key: {config.get('supabase_key', 'N/A')[:10]}...")
    console.print(f"  Default Model: {config.get('default_model', 'N/A')}")
