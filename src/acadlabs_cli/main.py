# main.py - bagian import atas
import typer
import uuid
from datetime import datetime, timezone
from rich.console import Console
from rich.prompt import Prompt
from acadlabs_cli.client.supabase import login_user, login_with_google, save_chat_to_db, save_message_to_db, supabase
from acadlabs_cli.client.openrouter import ask_ai

app = typer.Typer(name="acadlabs", help="AI-powered coding assistant CLI", add_completion=True)
console = Console()

@app.command(name="login-google")
def login_google():
    """Login dengan Google OAuth (buka browser)"""
    console.print("[bold blue]🔐 Login dengan Google[/bold blue]\n")
    console.print("Browser akan terbuka untuk autentikasi Google.\n")
    
    success = login_with_google()
    if success:
        console.print("[green]🎉 Siap digunakan![/green]")
    else:
        console.print("[yellow]⚠️ Login tidak selesai.[/yellow]")

@app.command()
def login():
    """Login ke akun Acadlabs (Supabase Auth)"""
    email = Prompt.ask("📧 Email")
    password = Prompt.ask("🔒 Password", password=True)
    
    user_data = login_user(email, password)
    if user_data:
        console.print("[green]✅ Login berhasil! Session disimpan lokal.[/green]")
    else:
        console.print("[red]❌ Login gagal. Cek email/password kamu.[/red]")

@app.command()
def chat():
    """Mulai sesi chat interaktif dengan AI"""
    # Cek session login
    try:
        user = supabase.auth.get_user()
        if not user:
            console.print("[yellow]⚠️ Kamu belum login. Jalankan 'acadlabs login' dulu.[/yellow]")
            return
        user_id = user.user.id
    except Exception:
        console.print("[red]🔐 Session expired. Jalankan 'acadlabs login' lagi.[/red]")
        return

    # Generate ID chat session
    chat_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    console.print("[bold blue]🤖 Acadlabs AI Ready. Ketik 'exit' untuk keluar.[/bold blue]")
    
    chat_history = []  # Simpan konteks untuk AI
    chat_title = None  # Akan diisi dari pesan pertama

    while True:
        try:
            prompt = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if prompt.lower() in ["exit", "quit", "keluar"]:
                console.print("[yellow]👋 Goodbye! Session tersimpan.[/yellow]")
                break

            # Set judul chat dari pesan pertama
            if chat_title is None:
                chat_title = prompt[:50] + ("..." if len(prompt) > 50 else "")
                save_chat_to_db(chat_id, user_id, chat_title, now)

            # Tanya AI
            with console.status("[bold green] Sedang berpikir...[/bold green]"):
                ai_response = ask_ai(prompt, chat_history)

            # Tampilkan jawaban
            console.print(f"\n[bold yellow]Acadlabs:[/bold yellow] {ai_response}")

            # Update history context
            chat_history.append({"role": "user", "content": prompt})
            chat_history.append({"role": "assistant", "content": ai_response})

            # Simpan ke database
            save_message_to_db(str(uuid.uuid4()), "user", prompt, chat_id, user_id, now)
            save_message_to_db(str(uuid.uuid4()), "assistant", ai_response, chat_id, user_id, now)

        except KeyboardInterrupt:
            console.print("\n[yellow]⌨️ Interrupted. Ketik 'exit' untuk keluar.[/yellow]")
            continue

if __name__ == "__main__":
    app()