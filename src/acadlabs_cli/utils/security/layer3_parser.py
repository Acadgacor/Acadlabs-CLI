"""
LAYER 3: ANTI-INJECTION - Isolasi Parameter Eksekusi

Mencegah command injection dengan:
1. shell=False (OS tidak interpret karakter spesial)
2. Parse command string menjadi list aman
3. Deteksi dan blokir karakter injeksi
"""
import re
import os
import shlex
from typing import Optional, Tuple, List

from rich.console import Console
from rich.panel import Panel


# Karakter yang berbahaya jika diinterpret oleh shell
INJECTION_CHARACTERS = {'&&', '||', '|', ';', '`', '$(', '${', '>', '>>', '<', '<<', '\n', '\r'}

# Pattern untuk mendeteksi injection attempt
INJECTION_PATTERNS = [
    r'&&',           # Command chaining
    r'\|\|',         # OR chaining
    r'\|',           # Pipe
    r';',            # Command separator
    r'`[^`]+`',      # Backtick command substitution
    r'\$\([^)]+\)',  # $() command substitution
    r'\$\{[^}]+\}',  # ${} variable expansion
    r'>',            # Output redirect
    r'<',            # Input redirect
    r'\n',           # Newline injection
    r'\r',           # Carriage return injection
]


class CommandInjectionError(Exception):
    """Raised when command injection is detected (Layer 3)"""
    pass


class CommandParser:
    """
    Layer 3 Security: Parse command string safely untuk mencegah injection.
    
    Menggunakan shlex untuk parsing yang aman dan shell=False untuk eksekusi.
    """
    
    def __init__(self):
        self.injection_patterns = INJECTION_PATTERNS
        self.injection_chars = INJECTION_CHARACTERS
    
    def detect_injection(self, command: str) -> Tuple[bool, List[str]]:
        """
        Detect potential injection attempts in command string.
        Returns (has_injection, list_of_detected_patterns)
        """
        detected = []
        
        for pattern in self.injection_patterns:
            matches = re.findall(pattern, command)
            if matches:
                detected.extend(matches if isinstance(matches, list) else [matches])
        
        return len(detected) > 0, detected
    
    def parse_safe(self, command: str, console: Optional[Console] = None) -> List[str]:
        """
        Parse command string into safe list format.
        
        Raises CommandInjectionError if injection detected.
        Returns list of arguments safe for subprocess.run(cmd_list, shell=False)
        """
        # Step 1: Detect injection attempts
        has_injection, detected = self.detect_injection(command)
        
        if has_injection:
            if console:
                console.print(Panel(
                    f"[bold red]LAYER 3: Injection Terdeteksi![/bold red]\n\n"
                    f"[yellow]Command:[/yellow] [cyan]{command}[/cyan]\n\n"
                    f"[yellow]Karakter berbahaya:[/yellow] {detected}\n\n"
                    f"[dim]Tip: Gunakan run_command_safe() dengan list args untuk command yang aman[/dim]",
                    title="Anti-Injection Protection",
                    border_style="red",
                ))
            raise CommandInjectionError(
                f"Command injection terdeteksi: {detected}. "
                f"Gunakan run_command_safe() dengan list args."
            )
        
        
        # Step 2: Parse dengan shlex (handles quotes, escapes, dll)
        try:
            # Untuk Windows, perlu handle path dengan backslash
            if os.name == 'nt':
                # shlex tidak handle backslash dengan baik di Windows
                # jadi kita gunakan mode POSIX=False
                parsed = shlex.split(command, posix=False)
                # Remove quotes dari hasil parse
                parsed = [arg.strip('"').strip("'") for arg in parsed]
            else:
                parsed = shlex.split(command)
        except ValueError as e:
            raise CommandInjectionError(f"Gagal parse command: {e}")
        
        return parsed
    
    def is_safe_for_shell_true(self, command: str) -> bool:
        """
        Check if command is safe enough for shell=True execution.
        (Digunakan untuk command yang memang perlu shell features)
        """
        has_injection, _ = self.detect_injection(command)
        return not has_injection


# Global parser instance
command_parser = CommandParser()
