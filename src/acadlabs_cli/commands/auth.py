"""
Authentication Commands

Command untuk login dan autentikasi user.
"""
import typer
from rich.console import Console
from rich.prompt import Prompt

from acadlabs_cli.client.supabase import login_user, login_with_google, supabase

console = Console()
app = typer.Typer(name="auth", help="Authentication commands")


@app.command(name="login-google")
def login_google():
    """Login dengan Google OAuth (buka browser)"""
    console.print("[bold blue]Login dengan Google[/bold blue]\n")
    console.print("Browser akan terbuka untuk autentikasi Google.\n")
    
    success = login_with_google()
    if success:
        console.print("[green]Siap digunakan![/green]")
    else:
        console.print("[yellow]Login tidak selesai.[/yellow]")


@app.command()
def login():
    """Login ke akun Acadlabs (Supabase Auth)"""
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    
    user_data = login_user(email, password)
    if user_data:
        console.print("[green]Login berhasil! Session disimpan lokal.[/green]")
    else:
        console.print("[red]Login gagal. Cek email/password kamu.[/red]")


@app.command()
def logout():
    """Logout dari akun Acadlabs"""
    try:
        supabase.auth.sign_out()
        console.print("[green]Logout berhasil![/green]")
    except Exception as e:
        console.print(f"[yellow]Note: {e}[/yellow]")


@app.command()
def status():
    """Cek status login saat ini"""
    try:
        user = supabase.auth.get_user()
        if user:
            console.print(f"[green]Logged in as: {user.user.email}[/green]")
        else:
            console.print("[yellow]Belum login.[/yellow]")
    except Exception:
        console.print("[red]Session expired atau tidak valid.[/red]")
