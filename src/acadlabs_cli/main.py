import typer
import uuid
from datetime import datetime, timezone
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from acadlabs_cli.client.supabase import login_user, login_with_google, save_chat_to_db, save_message_to_db, supabase
from acadlabs_cli.client.openrouter import ask_ai_with_tools
from acadlabs_cli.utils.tools import get_tools_schema, TOOLS_REGISTRY, SAFE_TOOLS, DANGEROUS_TOOLS, get_project_context, git_status
from acadlabs_cli.utils.agentic_loop import AgenticLoop, AgenticConfig, create_agentic_loop
from acadlabs_cli.utils.token_manager import (
    TokenManager,
    create_token_manager,
    estimate_history_tokens,
    check_and_prompt_clear
)

app = typer.Typer(name="acadlabs", help="AI-powered coding assistant CLI", add_completion=True)
console = Console()

# Agentic Loop dengan konfigurasi
agentic_config = AgenticConfig(
    max_iterations=15,
    max_tools_per_iteration=5,
    auto_approve_safe=True,
    auto_approve_dangerous=False,  # Dangerous tools WAJIB konfirmasi
    show_thinking=True,
    verbose=True
)
agentic_loop = create_agentic_loop(
    max_iterations=15,
    auto_approve_safe=True,
    auto_approve_dangerous=False,
    verbose=True
)
tools_schema = get_tools_schema()

# Token manager untuk tracking dan warning
token_manager = create_token_manager()

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
    """Mulai sesi chat interaktif dengan AI + Agentic Loop (ReAct Pattern)"""
    # Cek session login
    try:
        user = supabase.auth.get_user()
        if not user:
            console.print("[yellow]Warning: Kamu belum login. Jalankan 'acadlabs login' dulu.[/yellow]")
            return
        user_id = user.user.id
    except Exception:
        console.print("[red]Session expired. Jalankan 'acadlabs login' lagi.[/red]")
        return

    # Generate ID chat session
    chat_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    console.print(Panel(
        "[bold blue]Acadlabs AI dengan Agentic Loop[/bold blue]\n\n"
        "[green]Mode: ReAct (Reason-Act-Observe)[/green]\n\n"
        "[dim]AI akan melakukan perulangan mandiri:\n"
        "1. REASON - Menganalisis dan memutuskan aksi\n"
        "2. ACT - Memanggil tools (dengan konfirmasi untuk aksi berbahaya)\n"
        "3. OBSERVE - Mengamati hasil dan melanjutkan sampai selesai[/dim]\n\n"
        "[dim]Commands: 'exit' untuk keluar, 'tools' untuk lihat tools, 'tokens' untuk status token, 'clear' untuk clear context[/dim]",
        title="Agentic Mode",
        border_style="blue"
    ))
    
    # ============================================
    # AUTO CONTEXT INJECTION - AI tahu projectnya
    # ============================================
    console.print("\n[cyan]Memuat konteks project...[/cyan]")
    
    project_context = get_project_context(max_depth=2)
    git_changes = git_status()
    
    # Build system context message
    system_context = f"""[SYSTEM CONTEXT - Otomatis dimuat]
Kamu sedang bekerja di project berikut:

{project_context}

Perubahan terakhir (git status):
{git_changes}

[END SYSTEM CONTEXT]

PENTING: Kamu sudah tahu konteks project ini. Jangan tanya user tentang struktur project kecuali perlu detail lebih lanjut. User mungkin baru saja memodifikasi file yang ditampilkan di git status di atas.
"""
    
    # Inject sebagai system message (tidak terlihat user tapi AI tahu)
    chat_history = [{"role": "system", "content": system_context}]
    
    # Tampilkan ringkasan ke user
    console.print("[green]Konteks project dimuat.[/green]")
    if "Modified files" in git_changes or "Working tree clean" not in git_changes:
        console.print(f"[yellow]Ada file yang dimodifikasi. AI akan mempertimbangkan perubahan ini.[/yellow]")
    
    chat_title = None  # Akan diisi dari pesan pertama
    total_tools_executed = 0  # Track total tools
    session_prompt_tokens = 0  # Track session tokens
    session_completion_tokens = 0

    while True:
        try:
            prompt = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if prompt.lower() in ["exit", "quit", "keluar"]:
                console.print(f"\n[green]Total tools executed this session: {total_tools_executed}[/green]")
                console.print("[yellow]Goodbye! Session tersimpan.[/yellow]")
                break
            
            if prompt.lower() == "tools":
                _show_available_tools()
                continue
            
            # Token status command
            if prompt.lower() == "tokens":
                _show_token_status(token_manager, chat_history, session_prompt_tokens, session_completion_tokens)
                continue
            
            # Clear context command
            if prompt.lower() == "clear":
                chat_history = [{"role": "system", "content": system_context}]
                token_manager.reset()
                session_prompt_tokens = 0
                session_completion_tokens = 0
                console.print("[green]Context cleared! Session fresh start.[/green]")
                continue

            # Set judul chat dari pesan pertama
            if chat_title is None:
                chat_title = prompt[:50] + ("..." if len(prompt) > 50 else "")
                save_chat_to_db(chat_id, user_id, chat_title, now)

            # ============================================
            # TOKEN CHECK - Warning jika context terlalu panjang
            # ============================================
            current_tokens = estimate_history_tokens(chat_history)
            if current_tokens >= token_manager.warning_threshold:
                should_clear, new_history = check_and_prompt_clear(chat_history, token_manager)
                if should_clear:
                    chat_history = new_history
                    if not chat_history:  # If cleared, re-inject system context
                        chat_history = [{"role": "system", "content": system_context}]
                    console.print("[green]Context cleared! Melanjutkan dengan fresh context.[/green]")
            
            # ============================================
            # AGENTIC LOOP - ReAct Pattern
            # ============================================
            # AI akan melakukan perulangan mandiri:
            # REASON -> ACT -> OBSERVE -> REASON -> ... sampai selesai
            
            final_response, loop_state, execution_log = agentic_loop.run(
                user_message=prompt,
                ask_ai_func=ask_ai_with_tools,
                history=chat_history,
                tools_schema=tools_schema
            )
            
            # Update total tools
            total_tools_executed += loop_state.total_tools_called
            
            # Update session tokens
            session_prompt_tokens += loop_state.prompt_tokens
            session_completion_tokens += loop_state.completion_tokens
            
            # Tampilkan response final
            if final_response:
                console.print(f"\n[bold yellow]Acadlabs:[/bold yellow] {final_response}")
            
            # Update history
            chat_history.append({"role": "user", "content": prompt})
            chat_history.append({"role": "assistant", "content": final_response or "(task completed)"})
            
            # Simpan ke database
            save_message_to_db(str(uuid.uuid4()), "user", prompt, chat_id, user_id, now)
            save_message_to_db(str(uuid.uuid4()), "assistant", final_response or "(completed)", chat_id, user_id, now)

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Ketik 'exit' untuk keluar.[/yellow]")
            continue


def _show_token_status(
    token_manager: TokenManager,
    chat_history: list,
    session_prompt: int,
    session_completion: int
):
    """Tampilkan status token usage"""
    from rich.table import Table
    
    history_tokens = estimate_history_tokens(chat_history)
    usage_percent = (history_tokens / token_manager.context_limit) * 100
    cost = token_manager.estimate_cost()
    
    console.print("\n[bold cyan]Token Status[/bold cyan]")
    console.print("=" * 50)
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Model", token_manager.model)
    table.add_row("Context Limit", f"{token_manager.context_limit:,}")
    table.add_row("Warning Threshold", f"{token_manager.warning_threshold:,}")
    table.add_row("Critical Threshold", f"{token_manager.critical_threshold:,}")
    table.add_row("Danger Threshold", f"{token_manager.danger_threshold:,}")
    table.add_row("", "")
    table.add_row("History Tokens", f"{history_tokens:,} ({usage_percent:.1f}%)")
    table.add_row("Session Prompt Tokens", f"{session_prompt:,}")
    table.add_row("Session Completion Tokens", f"{session_completion:,}")
    table.add_row("Total Session Tokens", f"{session_prompt + session_completion:,}")
    table.add_row("", "")
    table.add_row("Estimated Cost", f"${cost:.4f} USD")
    
    console.print(table)
    
    # Warning status
    if history_tokens >= token_manager.danger_threshold:
        console.print("\n[red bold]⚠️ DANGER: Context hampir penuh! Ketik 'clear' untuk clear context.[/red bold]")
    elif history_tokens >= token_manager.critical_threshold:
        console.print("\n[orange3 bold]⚠️ CRITICAL: Context sudah tinggi. Pertimbangkan clear context.[/orange3 bold]")
    elif history_tokens >= token_manager.warning_threshold:
        console.print("\n[yellow bold]⚠️ WARNING: Context mulai panjang. Biaya akan meningkat.[/yellow bold]")
    else:
        console.print("\n[green]✅ Token usage dalam batas aman.[/green]")


def _show_available_tools():
    """Tampilkan daftar tools yang tersedia"""
    
    console.print("\n[bold cyan]Available Tools:[/bold cyan]")
    
    console.print("\n[green]Safe Tools (auto-approved):[/green]")
    for tool in TOOLS_REGISTRY:
        if tool.name in SAFE_TOOLS:
            console.print(f"  [cyan]{tool.name}[/cyan]: {tool.description}")
    
    console.print("\n[yellow]Dangerous Tools (need confirmation):[/yellow]")
    for tool in TOOLS_REGISTRY:
        if tool.name in DANGEROUS_TOOLS:
            console.print(f"  [yellow]{tool.name}[/yellow]: {tool.description}")
    
    console.print()

if __name__ == "__main__":
    app()