"""
Agentic Loop - ReAct Pattern (Reason, Act, Observe)

Implementasi perulangan mandiri AI yang memungkinkan AI untuk:
1. REASON: Menganalisis situasi dan memutuskan aksi
2. ACT: Memanggil tools untuk melakukan aksi
3. OBSERVE: Mengamati hasil dan memutuskan langkah selanjutnya

Loop berlanjut sampai AI menyatakan tugas selesai atau mencapai batas iterasi.
"""
import json
from typing import List, Dict, Any, Optional, Tuple, Callable

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

# Import config
from acadlabs_cli.core.agent.config import LoopStatus, LoopState, AgenticConfig

# Import token manager
from acadlabs_cli.utils.token_manager import (
    TokenManager,
    estimate_tokens,
    estimate_history_tokens,
    create_token_manager
)

console = Console()


class AgenticLoop:
    """
    Agentic Loop dengan pola ReAct.
    
    Flow:
    1. User memberikan task
    2. AI REASON: Menganalisis dan memutuskan aksi
    3. AI ACT: Memanggil tools (melewati security layers)
    4. AI OBSERVE: Melihat hasil dan memutuskan lanjut atau selesai
    5. Jika belum selesai, kembali ke step 2
    6. Jika selesai, return hasil ke user
    """
    
    def __init__(
        self,
        config: AgenticConfig = None,
        secure_executor=None,
        tool_registry=None,
        token_manager: TokenManager = None
    ):
        self.config = config or AgenticConfig()
        self.state = LoopState()
        
        # Import secure executor for dangerous operations
        if secure_executor is None:
            from acadlabs_cli.utils.security import secure_executor as se
            secure_executor = se
        self.secure_executor = secure_executor
        
        # Import tool registry
        if tool_registry is None:
            from acadlabs_cli.tools import (
                TOOLS_REGISTRY,
                execute_tool,
                is_dangerous_tool,
                get_tool_by_name
            )
            self.tool_registry = TOOLS_REGISTRY
            self.execute_tool_fn = execute_tool
            self.is_dangerous_tool_fn = is_dangerous_tool
            self.get_tool_by_name_fn = get_tool_by_name
        else:
            self.tool_registry = tool_registry
        
        # Token manager for tracking and warnings
        if token_manager is None:
            self.token_manager = create_token_manager()
        else:
            self.token_manager = token_manager
        
        # Callbacks
        self.on_iteration_start: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
        self.on_tool_result: Optional[Callable] = None
        self.on_iteration_end: Optional[Callable] = None
        self.on_token_warning: Optional[Callable] = None
    
    def run(
        self,
        user_message: str,
        ask_ai_func: Callable,
        history: List[Dict] = None,
        tools_schema: List[Dict] = None
    ) -> Tuple[str, LoopState, List[Dict]]:
        """
        Menjalankan agentic loop.
        
        Args:
            user_message: Pesan dari user
            ask_ai_func: Fungsi untuk memanggil AI (ask_ai_with_tools)
            history: Chat history
            tools_schema: Schema tools untuk AI
        
        Returns:
            (final_response, final_state, execution_log)
        """
        self.state = LoopState()  # Reset state
        execution_log = []
        
        if history is None:
            history = []
        
        console.print(Panel(
            f"[bold cyan]Memulai Agentic Loop[/bold cyan]\n"
            f"[dim]Max iterations: {self.config.max_iterations}[/dim]\n"
            f"[dim]Token warning at: {self.config.token_warning_threshold:,}[/dim]",
            title="Agentic Mode",
            border_style="cyan"
        ))
        
        current_message = user_message
        current_tool_calls = None
        
        while not self.state.is_complete:
            self.state.iteration += 1
            
            # Check max iterations
            if self.state.iteration > self.config.max_iterations:
                console.print(f"\n[yellow]Mencapai batas iterasi ({self.config.max_iterations})[/yellow]")
                self.state.is_complete = True
                break
            
            # ==========================================
            # TOKEN CHECK - Warning jika mendekati threshold
            # ==========================================
            if self.config.enable_token_warnings:
                current_tokens = estimate_history_tokens(history) if history else 0
                self.state.total_tokens = current_tokens
                
                if current_tokens >= self.config.token_warning_threshold:
                    self._display_token_warning(current_tokens)
                    
                    # Callback untuk token warning
                    if self.on_token_warning:
                        should_continue = self.on_token_warning(current_tokens, self.token_manager)
                        if not should_continue:
                            console.print("[yellow]Session dihentikan oleh user.[/yellow]")
                            self.state.is_complete = True
                            break
            
            # Callback: iteration start
            if self.on_iteration_start:
                self.on_iteration_start(self.state)
            
            if self.config.show_thinking:
                self._display_iteration_header()
            
            # ==========================================
            # STEP 1: REASON - AI menganalisis dan memutuskan
            # ==========================================
            with console.status(f"[bold green]Iteration {self.state.iteration}: AI berpikir...[/bold green]"):
                ai_response, tool_calls = ask_ai_func(
                    current_message,
                    history,
                    tools_schema
                )
            
            
            # Track tokens for this iteration
            prompt_tokens = estimate_tokens(current_message) + estimate_history_tokens(history[-3:] if history else [])
            completion_tokens = estimate_tokens(ai_response or "")
            self.state.prompt_tokens += prompt_tokens
            self.state.completion_tokens += completion_tokens
            self.state.total_tokens = self.state.prompt_tokens + self.state.completion_tokens
            
            # Update token manager
            self.token_manager.add_usage(prompt_tokens, completion_tokens, len(tool_calls) if tool_calls else 0)
            
            self.state.last_response = ai_response or ""
            
            # ==========================================
            # STEP 2: ACT - Eksekusi tools jika ada
            # ==========================================
            if tool_calls:
                self.state.tools_this_iteration = len(tool_calls)
                
                # Check max tools per iteration
                if self.state.tools_this_iteration > self.config.max_tools_per_iteration:
                    console.print(f"[yellow]Membatasi ke {self.config.max_tools_per_iteration} tools per iterasi[/yellow]")
                    tool_calls = tool_calls[:self.config.max_tools_per_iteration]
                
                # Execute tools
                tool_results, tool_log = self._execute_tools_with_security(tool_calls)
                execution_log.extend(tool_log)
                self.state.total_tools_called += len(tool_log)
                
                # Check if any tools were blocked
                blocked_count = sum(1 for t in tool_log if not t.get("approved", True))
                if blocked_count > 0:
                    self.state.blocked_actions.extend([
                        t["name"] for t in tool_log if not t.get("approved", True)
                    ])
                
                # ==========================================
                # STEP 3: OBSERVE - Kirim hasil ke AI untuk analisis
                # ==========================================
                # Build message untuk AI dengan tool results
                current_message = self._build_observation_message(tool_calls, tool_results)
                
                # Callback: iteration end
                if self.on_iteration_end:
                    self.on_iteration_end(self.state, tool_log)
            
            else:
                # Tidak ada tool calls - AI memberikan jawaban final
                self.state.is_complete = True
                
                if self.config.verbose:
                    console.print(f"\n[green]AI menyatakan tugas selesai[/green]")
        
        # Build final response
        final_response = self.state.last_response
        
        # Display summary
        self._display_summary(execution_log)
        
        # Display token summary
        self._display_token_summary()
        
        return final_response, self.state, execution_log
    
    def _execute_tools_with_security(self, tool_calls: List[Dict]) -> Tuple[List[str], List[Dict]]:
        """
        Eksekusi tools dengan integrasi security layers.
        
        Safe tools: Langsung dieksekusi
        Dangerous tools: Melewati 5-layer security system
        """
        results = []
        execution_log = []
        
        for tc in tool_calls:
            tool_id = tc["id"]
            tool_name = tc["name"]
            arguments = tc["arguments"]
            
            # Display tool call
            self._display_tool_call(tool_name, arguments)
            
            # Check if dangerous
            is_dangerous = self.is_dangerous_tool_fn(tool_name)
            
            if is_dangerous:
                # ==========================================
                # DANGEROUS TOOL - Melewati Security Layers
                # ==========================================
                result, approved = self._execute_dangerous_tool(tool_name, arguments)
            else:
                # ==========================================
                # SAFE TOOL - Langsung eksekusi
                # ==========================================
                if self.config.auto_approve_safe:
                    result = self.execute_tool_fn(tool_name, arguments)
                    approved = True
                else:
                    # Minta konfirmasi walau safe
                    approved = self._confirm_tool_execution(tool_name, arguments)
                    if approved:
                        result = self.execute_tool_fn(tool_name, arguments)
                    else:
                        result = f"Tool '{tool_name}' diblokir oleh user."
            
            results.append(result)
            
            # Log
            execution_log.append({
                "id": tool_id,
                "name": tool_name,
                "arguments": arguments,
                "result": result[:500] if len(result) > 500 else result,
                "approved": approved,
                "dangerous": is_dangerous,
                "iteration": self.state.iteration
            })
            
            # Display result
            self._display_tool_result(tool_name, result, approved)
        
        return results, execution_log
    
    def _execute_dangerous_tool(self, tool_name: str, arguments: Dict) -> Tuple[str, bool]:
        """
        Eksekusi dangerous tool melalui security layers.
        
        Integrasi dengan Layer 1-5:
        - Layer 1: Human confirmation (via SecureExecutor)
        - Layer 2: Whitelist validation
        - Layer 3: Anti-injection
        - Layer 4: Path locking
        - Layer 5: Containerization (opsional)
        """
        try:
            # Special handling untuk write_file
            if tool_name == "write_file":
                path = arguments.get("path", "")
                content = arguments.get("content", "")
                mode = arguments.get("mode", "w")
                
                # Gunakan secure_executor yang sudah terintegrasi dengan Layer 1-4
                self.secure_executor.write_file(path, content, mode)
                return f"Success: File written to '{path}'", True
            
            # Special handling untuk replace_code_block
            elif tool_name == "replace_code_block":
                path = arguments.get("path", "")
                old_code = arguments.get("old_code", "")
                new_code = arguments.get("new_code", "")
                replace_all = arguments.get("replace_all", False)
                
                # Gunakan secure_executor untuk konfirmasi user
                # Baca file dulu
                import os
                if not os.path.exists(path):
                    return f"Error: File not found: '{path}'", True
                
                with open(path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Cek apakah old_code ada
                if old_code not in file_content:
                    return f"Error: old_code tidak ditemukan di file '{path}'", True
                
                # Minta konfirmasi user melalui secure_executor
                approved = self._confirm_tool_execution(tool_name, {
                    "path": path,
                    "old_code": old_code[:100] + "..." if len(old_code) > 100 else old_code,
                    "new_code": new_code[:100] + "..." if len(new_code) > 100 else new_code,
                })
                
                if approved:
                    # Lakukan replacement
                    if replace_all:
                        new_content = file_content.replace(old_code, new_code)
                    else:
                        new_content = file_content.replace(old_code, new_code, 1)
                    
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    return f"Success: Code replaced in '{path}'", True
                else:
                    return f"Tool '{tool_name}' diblokir oleh user.", False
            
            # Special handling untuk run_terminal_command
            elif tool_name == "run_terminal_command":
                command = arguments.get("command", "")
                timeout = arguments.get("timeout", 30)
                
                # Gunakan secure_executor untuk command
                try:
                    result = self.secure_executor.run_command(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    output = result.stdout or result.stderr or "(no output)"
                    return output, True
                except Exception as e:
                    # Jika user menolak atau error
                    if "ditolak" in str(e) or "SecurityViolation" in str(e):
                        return f"Command diblokir oleh user: {command}", False
                    return f"Error: {e}", True
            
            # Default: gunakan execute_tool biasa dengan konfirmasi
            else:
                approved = self._confirm_tool_execution(tool_name, arguments)
                if approved:
                    result = self.execute_tool_fn(tool_name, arguments)
                    return result, True
                else:
                    return f"Tool '{tool_name}' diblokir oleh user.", False
        
        except Exception as e:
            error_msg = str(e)
            self.state.errors.append(error_msg)
            
            # Check if it's a security violation (user rejected)
            if "SecurityViolation" in error_msg or "ditolak" in error_msg:
                return f"Diblokir oleh security: {error_msg}", False
            
            return f"Error: {error_msg}", True
    
    def _confirm_tool_execution(self, tool_name: str, arguments: Dict) -> bool:
        """Minta konfirmasi user untuk eksekusi tool"""
        args_str = "\n".join([f"  {k}: {v}" for k, v in arguments.items()])
        
        console.print(Panel(
            f"[bold yellow]Tool:[/bold yellow] {tool_name}\n"
            f"[bold yellow]Arguments:[/bold yellow]\n{args_str}",
            title="Konfirmasi Eksekusi",
            border_style="yellow"
        ))
        
        from rich.prompt import Confirm
        return Confirm.ask("[bold red]Izinkan eksekusi?[/bold red]", default=False)
    
    def _build_observation_message(self, tool_calls: List[Dict], tool_results: List[str]) -> str:
        """Build pesan observasi untuk dikirim ke AI"""
        observations = []
        
        for tc, result in zip(tool_calls, tool_results):
            tool_name = tc["name"]
            observations.append(f"[Tool: {tool_name}]\nResult: {result}")
        
        return "Berikut hasil eksekusi tools:\n\n" + "\n\n".join(observations)
    
    def _display_iteration_header(self):
        """Tampilkan header iterasi"""
        console.print(f"\n[bold cyan]{'='*50}[/bold cyan]")
        console.print(f"[bold cyan]ITERASI {self.state.iteration}/{self.config.max_iterations}[/bold cyan]")
        console.print(f"[bold cyan]{'='*50}[/bold cyan]")
    
    def _display_tool_call(self, tool_name: str, arguments: Dict):
        """Tampilkan tool call"""
        is_dangerous = self.is_dangerous_tool_fn(tool_name)
        color = "yellow" if is_dangerous else "green"
        status = "[DANGER]" if is_dangerous else "[SAFE]"
        
        args_str = "\n".join([f"  {k}: {v}" for k, v in arguments.items()])
        
        console.print(Panel(
            f"[bold]Arguments:[/bold]\n{args_str}",
            title=f"[{color}]Tool Call {status}: {tool_name}[/{color}]",
            border_style=color
        ))
    
    def _display_tool_result(self, tool_name: str, result: str, approved: bool):
        """Tampilkan hasil tool"""
        # Truncate jika terlalu panjang
        display_result = result
        if len(result) > 800:
            display_result = result[:800] + "\n... (truncated)"
        
        color = "green" if approved else "red"
        status = "APPROVED" if approved else "BLOCKED"
        
        console.print(Panel(
            display_result,
            title=f"[{color}]Result [{status}]: {tool_name}[/{color}]",
            border_style=color
        ))
    
    def _display_token_warning(self, current_tokens: int):
        """Tampilkan warning ketika token mendekati threshold"""
        usage_percent = (current_tokens / self.token_manager.context_limit) * 100
        cost = self.token_manager.estimate_cost()
        
        # Determine warning level
        if current_tokens >= self.token_manager.danger_threshold:
            level = "DANGER"
            color = "red"
        elif current_tokens >= self.token_manager.critical_threshold:
            level = "CRITICAL"
            color = "orange3"
        else:
            level = "WARNING"
            color = "yellow"
        
        console.print(Panel(
            f"[bold {color}]Context Window {level}![/bold {color}]\n\n"
            f"Token Usage: [bold]{current_tokens:,}[/bold] / {self.token_manager.context_limit:,} ({usage_percent:.1f}%)\n"
            f"Estimated Cost: [bold]${cost:.4f} USD[/bold]\n\n"
            f"[dim]Biaya prompt akan mulai mahal karena context yang panjang.[/dim]\n"
            f"[dim]Pertimbangkan untuk clear context atau mulai session baru.[/dim]\n\n"
            f"[cyan]Ketik 'clear' untuk menghapus context atau 'continue' untuk melanjutkan.[/cyan]",
            title=f"[{color}]Token Warning[/{color}]",
            border_style=color
        ))
        
        # Prompt user for action
        from rich.prompt import Prompt
        choice = Prompt.ask(
            "\n[bold]Pilihan[/bold]",
            choices=["clear", "continue", "status"],
            default="continue"
        )
        
        if choice == "clear":
            console.print("[green]Context akan di-clear setelah iterasi ini.[/green]")
            # Signal to clear history
            self._should_clear_context = True
        elif choice == "status":
            self.token_manager.display_status()
    
    def _display_token_summary(self):
        """Tampilkan ringkasan token usage"""
        cost = self.token_manager.estimate_cost()
        usage_percent = (self.state.total_tokens / self.token_manager.context_limit) * 100
        
        console.print("\n" + "="*50)
        console.print("[bold cyan]TOKEN USAGE SUMMARY[/bold cyan]")
        console.print("="*50)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Prompt Tokens", f"{self.state.prompt_tokens:,}")
        table.add_row("Completion Tokens", f"{self.state.completion_tokens:,}")
        table.add_row("Total Tokens", f"{self.state.total_tokens:,}")
        table.add_row("Context Usage", f"{usage_percent:.1f}%")
        table.add_row("Estimated Cost", f"${cost:.4f} USD")
        table.add_row("Model", self.token_manager.model)
        
        console.print(table)
    
    def _display_summary(self, execution_log: List[Dict]):
        """Tampilkan ringkasan eksekusi"""
        console.print("\n" + "="*50)
        console.print("[bold cyan]RINGKASAN AGENTIC LOOP[/bold cyan]")
        console.print("="*50)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Iterasi", str(self.state.iteration))
        table.add_row("Total Tools Dipanggil", str(self.state.total_tools_called))
        table.add_row("Aksi Diblokir", str(len(self.state.blocked_actions)))
        table.add_row("Errors", str(len(self.state.errors)))
        
        console.print(table)
        
        # Tampilkan log detail jika verbose
        if self.config.verbose and execution_log:
            console.print("\n[bold]Execution Log:[/bold]")
            for i, entry in enumerate(execution_log, 1):
                status = "[green]OK[/green]" if entry["approved"] else "[red]BLOCKED[/red]"
                danger = "[yellow]DANGER[/yellow]" if entry["dangerous"] else "[dim]safe[/dim]"
                console.print(f"  {i}. {entry['name']} {danger} {status}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_agentic_loop(
    max_iterations: int = 15,
    auto_approve_safe: bool = True,
    auto_approve_dangerous: bool = False,
    verbose: bool = True
) -> AgenticLoop:
    """Factory function untuk membuat AgenticLoop dengan konfigurasi custom"""
    config = AgenticConfig(
        max_iterations=max_iterations,
        auto_approve_safe=auto_approve_safe,
        auto_approve_dangerous=auto_approve_dangerous,
        verbose=verbose
    )
    return AgenticLoop(config=config)


# Default instance
agentic_loop = AgenticLoop()
