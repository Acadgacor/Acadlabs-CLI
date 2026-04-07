"""Tool Executor - Handles AI tool calls with Human-in-the-Loop confirmation"""
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from acadlabs_cli.utils.tools import (
    execute_tool,
    is_dangerous_tool,
    get_tool_by_name,
    SAFE_TOOLS,
    DANGEROUS_TOOLS,
)

console = Console()


class ToolExecutor:
    """
    Mengeksekusi tool calls dari AI dengan sistem konfirmasi.
    
    Flow:
    1. AI memanggil tool
    2. Jika tool berbahaya -> minta konfirmasi user
    3. Eksekusi tool
    4. Return hasil ke AI
    """
    
    def __init__(self, auto_approve_safe: bool = True, auto_approve_dangerous: bool = False):
        """
        Args:
            auto_approve_safe: Auto-approve safe tools (read, list, search)
            auto_approve_dangerous: Auto-approve dangerous tools (write, exec)
                                    WARNING: Set True hanya untuk testing!
        """
        self.auto_approve_safe = auto_approve_safe
        self.auto_approve_dangerous = auto_approve_dangerous
        self.execution_log = []  # Log semua eksekusi
    
    def process_tool_calls(self, tool_calls: List[Dict]) -> Tuple[List[str], List[Dict]]:
        """
        Process multiple tool calls dari AI.
        
        Args:
            tool_calls: List dari {"id": str, "name": str, "arguments": dict}
        
        Returns:
            (results, executed_tools) - Hasil eksekusi dan info tool yang dieksekusi
        """
        results = []
        executed_tools = []
        
        for tc in tool_calls:
            tool_id = tc["id"]
            tool_name = tc["name"]
            arguments = tc["arguments"]
            
            # Display tool call
            self._display_tool_call(tool_name, arguments)
            
            # Check if dangerous and need confirmation
            if is_dangerous_tool(tool_name):
                approved = self._confirm_dangerous_tool(tool_name, arguments)
                if not approved:
                    results.append(f"Tool '{tool_name}' diblokir oleh user.")
                    executed_tools.append({
                        "id": tool_id,
                        "name": tool_name,
                        "arguments": arguments,
                        "result": "BLOCKED",
                        "approved": False
                    })
                    continue
            
            # Execute tool
            result = execute_tool(tool_name, arguments)
            results.append(result)
            
            # Log execution
            executed_tools.append({
                "id": tool_id,
                "name": tool_name,
                "arguments": arguments,
                "result": result[:500] if len(result) > 500 else result,  # Truncate for log
                "approved": True
            })
            
            self.execution_log.append(executed_tools[-1])
            
            # Display result
            self._display_tool_result(tool_name, result)
        
        return results, executed_tools
    
    def _display_tool_call(self, tool_name: str, arguments: Dict):
        """Tampilkan tool call ke user"""
        # Format arguments
        args_str = "\n".join([f"  {k}: {v}" for k, v in arguments.items()])
        
        color = "yellow" if is_dangerous_tool(tool_name) else "cyan"
        
        console.print(Panel(
            f"[bold]Arguments:[/bold]\n{args_str}",
            title=f"[{color}]Tool Call: {tool_name}[/{color}]",
            border_style=color,
        ))
    
    def _display_tool_result(self, tool_name: str, result: str):
        """Tampilkan hasil eksekusi tool"""
        # Truncate jika terlalu panjang
        display_result = result
        if len(result) > 1000:
            display_result = result[:1000] + "\n... (truncated)"
        
        console.print(Panel(
            display_result,
            title=f"[green]Result: {tool_name}[/green]",
            border_style="green",
        ))
    
    def _confirm_dangerous_tool(self, tool_name: str, arguments: Dict) -> bool:
        """
        Minta konfirmasi user untuk tool berbahaya.
        
        Returns:
            True jika disetujui, False jika ditolak
        """
        if self.auto_approve_dangerous:
            console.print("[yellow]Auto-approve dangerous tool (testing mode)[/yellow]")
            return True
        
        # Get tool info
        tool = get_tool_by_name(tool_name)
        tool_desc = tool.description if tool else "Unknown tool"
        
        # Build warning message
        args_display = "\n".join([f"  [cyan]{k}:[/cyan] {v}" for k, v in arguments.items()])
        
        console.print()
        console.print(Panel(
            f"[bold red]AI ingin menjalankan tool berbahaya:[/bold red]\n\n"
            f"[yellow]Tool:[/yellow] {tool_name}\n"
            f"[yellow]Deskripsi:[/yellow] {tool_desc}\n\n"
            f"[yellow]Arguments:[/yellow]\n{args_display}",
            title="Peringatan Keamanan",
            border_style="red",
        ))
        
        return Confirm.ask(
            "\n[bold red]Izinkan eksekusi tool ini?[/bold red]",
            default=False
        )
    
    def get_execution_summary(self) -> str:
        """Dapatkan ringkasan semua eksekusi di sesi ini"""
        if not self.execution_log:
            return "No tools executed yet."
        
        table = Table(title="Tool Execution Log")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Result Preview", style="dim")
        
        for entry in self.execution_log:
            status = "APPROVED" if entry["approved"] else "BLOCKED"
            status_style = "green" if entry["approved"] else "red"
            result_preview = entry["result"][:50] + "..." if len(entry["result"]) > 50 else entry["result"]
            
            table.add_row(
                entry["name"],
                f"[{status_style}]{status}[/{status_style}]",
                result_preview
            )
        
        console.print(table)
        return f"Total: {len(self.execution_log)} tools executed"


class ToolCallHandler:
    """
    High-level handler untuk mengelola seluruh tool calling workflow.
    Menghubungkan AI response -> tool execution -> AI follow-up.
    """
    
    def __init__(self, executor: ToolExecutor = None):
        self.executor = executor or ToolExecutor()
    
    def handle_tool_calls_loop(
        self,
        initial_response: str,
        tool_calls: List[Dict],
        history: list,
        send_results_func
    ) -> Tuple[str, List[Dict]]:
        """
        Handle tool calls dengan loop sampai AI selesai.
        
        Args:
            initial_response: Teks response awal dari AI
            tool_calls: Tool calls dari AI
            history: Chat history
            send_results_func: Fungsi untuk mengirim results ke AI
                               (dari openrouter.send_tool_results)
        
        Returns:
            (final_response, all_executed_tools)
        """
        all_executed = []
        current_tool_calls = tool_calls
        current_response = initial_response
        
        # Loop untuk handle multiple rounds of tool calls
        max_iterations = 10  # Prevent infinite loop
        iteration = 0
        
        while current_tool_calls and iteration < max_iterations:
            iteration += 1
            
            console.print(f"\n[dim]Tool calling iteration {iteration}...[/dim]")
            
            # Execute tools
            results, executed = self.executor.process_tool_calls(current_tool_calls)
            all_executed.extend(executed)
            
            # Send results back to AI
            current_response, current_tool_calls = send_results_func(
                history, current_tool_calls, results
            )
            
            # Update history dengan tool results
            # (history akan diupdate di main loop)
        
        return current_response, all_executed


# Singleton instance
tool_executor = ToolExecutor()
tool_call_handler = ToolCallHandler()
