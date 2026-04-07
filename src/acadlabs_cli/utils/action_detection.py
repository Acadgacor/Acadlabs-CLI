"""Human-in-the-Loop action confirmation system"""
import re
from typing import List, Tuple

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel


console = Console()


# Patterns for dangerous actions that require confirmation
DANGEROUS_PATTERNS = {
    "file_delete": [
        r"\brm\s+-rf\b",
        r"\brm\s+-f\b",
        r"\brmdir\b",
        r"\bdel\s+/[sS]\b",
        r"\bRemove-Item\b",
        r"\bDelete\b.*file",
        r"\bshutil\.rmtree\b",
        r"\bos\.remove\b",
        r"\bos\.unlink\b",
    ],
    "file_write": [
        r"\bwith\s+open\([^)]+['\"]w['\"]",
        r"\bfile\.write\b",
        r"\bwrite_to_file\b",
        r"\bcreate\s+(?:a\s+)?file\b",
        r"\bmodify\s+(?:the\s+)?file\b",
        r"\bedit\s+(?:the\s+)?file\b",
    ],
    "command_exec": [
        r"\bsubprocess\.run\b",
        r"\bos\.system\b",
        r"\bexec\(",
        r"\beval\(",
        r"\bpopen\b",
        r"&&\s*\w+",  # chained commands
        r"\|\s*\w+",  # piped commands
    ],
    "package_install": [
        r"\bpip\s+install\b",
        r"\bnpm\s+install\b",
        r"\byarn\s+add\b",
        r"\bapt\s+install\b",
        r"\bbrew\s+install\b",
    ],
    "git_operations": [
        r"\bgit\s+push\b",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+clean\s+-fd\b",
        r"\bgit\s+checkout\s+--\.",
    ],
}

# Action descriptions for user-friendly messages
ACTION_DESCRIPTIONS = {
    "file_delete": "menghapus file/direktori",
    "file_write": "menulis/mengubah file",
    "command_exec": "menjalankan command sistem",
    "package_install": "menginstall package",
    "git_operations": "melakukan operasi git berbahaya",
}


class ActionDetector:
    """Detect and categorize dangerous actions in AI responses"""
    
    def __init__(self):
        self.patterns = DANGEROUS_PATTERNS
    
    def detect(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Detect dangerous actions in text.
        Returns list of (action_type, matched_pattern, matched_text)
        """
        detected = []
        
        for action_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    detected.append((action_type, pattern, match.group()))
        
        return detected
    
    def has_dangerous_action(self, text: str) -> bool:
        """Check if text contains any dangerous action"""
        return len(self.detect(text)) > 0


class ActionConfirmator:
    """Handle human-in-the-loop confirmation for dangerous actions"""
    
    def __init__(self, auto_approve_safe: bool = False):
        self.detector = ActionDetector()
        self.auto_approve_safe = auto_approve_safe
        self.approved_actions = set()
    
    def confirm_action(self, action_type: str, action_detail: str, full_response: str) -> bool:
        """
        Ask user confirmation for a dangerous action.
        Returns True if approved, False otherwise.
        """
        description = ACTION_DESCRIPTIONS.get(action_type, "melakukan aksi berbahaya")
        
        console.print()
        console.print(Panel(
            f"[bold red]AI mencoba {description}[/bold red]\n\n"
            f"[yellow]Detail:[/yellow] {action_detail}\n\n"
            f"[dim]Konteks: {full_response[:200]}...[/dim]",
            title="Peringatan Keamanan",
            border_style="red",
        ))
        
        is_allowed = Confirm.ask(
            f"[bold red]Izinkan aksi ini?[/bold red]",
            default=False
        )
        
        if is_allowed:
            console.print("[green]Aksi diizinkan.[/green]")
            return True
        else:
            console.print("[yellow]Aksi dibatalkan oleh pengguna.[/yellow]")
            return False
    
    def confirm_response(self, ai_response: str) -> Tuple[bool, str]:
        """
        Check AI response for dangerous actions and request confirmation.
        Returns (is_approved, modified_response)
        """
        detected_actions = self.detector.detect(ai_response)
        
        if not detected_actions:
            return True, ai_response
        
        # Group by action type to avoid duplicate confirmations
        confirmed_types = set()
        cancelled = False
        
        for action_type, pattern, matched_text in detected_actions:
            if action_type in confirmed_types:
                continue
            
            if not self.confirm_action(action_type, matched_text, ai_response):
                cancelled = True
                break
            
            confirmed_types.add(action_type)
        
        if cancelled:
            return False, "[yellow]Aksi dibatalkan. Silakan minta AI untuk alternatif yang lebih aman.[/yellow]"
        
        return True, ai_response
    
    def confirm_command_execution(self, command: str) -> bool:
        """
        Specifically confirm before executing a shell command.
        """
        console.print()
        console.print(Panel(
            f"[bold red]AI ingin menjalankan command:[/bold red]\n\n"
            f"[cyan]{command}[/cyan]",
            title="Eksekusi Command",
            border_style="yellow",
        ))
        
        return Confirm.ask(
            "[bold red]Jalankan command ini?[/bold red]",
            default=False
        )
    
    def confirm_file_operation(self, operation: str, filepath: str) -> bool:
        """
        Confirm before file operations.
        """
        console.print()
        console.print(Panel(
            f"[bold red]AI ingin {operation}:[/bold red]\n\n"
            f"[cyan]{filepath}[/cyan]",
            title="Operasi File",
            border_style="yellow",
        ))
        
        return Confirm.ask(
            f"[bold red]{operation.title()} file ini?[/bold red]",
            default=False
        )


def create_action_confirmator() -> ActionConfirmator:
    """Factory function to create ActionConfirmator instance"""
    return ActionConfirmator()


# Global instance for easy import
action_confirmator = ActionConfirmator()
