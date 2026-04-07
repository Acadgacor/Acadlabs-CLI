"""
LAYER 2: COMMAND WHITELIST - Validasi Perintah

Lebih aman dari blacklist: HANYA perintah dalam whitelist yang diizinkan
Semua perintah di luar whitelist ditolak OTOMATIS tanpa konfirmasi
"""
import re
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel


# Whitelist command yang diizinkan (prefix-based)
COMMAND_WHITELIST = {
    # Package managers
    "npm", "npx", "yarn", "pnpm",
    "pip", "python", "python3", "py",
    
    # Version control
    "git",
    
    # Runtime/Build tools
    "node", "deno", "bun",
    "cargo", "rustc",
    "go",
    
    # Development tools
    "make", "cmake",
    "docker", "docker-compose",
    
    # File operations (safe ones)
    "ls", "dir", "cat", "type", "head", "tail",
    "find", "grep", "rg", "fd",
    "tree",
    
    # Process management
    "ps", "kill", "top", "htop",
    
    # Network (read-only)
    "curl", "wget", "ping",
    
    # Misc safe commands
    "echo", "pwd", "which", "where", "whoami",
    "date", "time",
    "env", "printenv",
}

# Commands that are NEVER allowed (even if in whitelist, these specific patterns are blocked)
COMMAND_BLACKLIST_PATTERNS = [
    r"\brm\s+-rf\s+/",           # rm -rf /
    r"\brm\s+-rf\s+~",           # rm -rf ~
    r"\brm\s+-rf\s+\*",          # rm -rf *
    r"\bformat\b",               # format drive
    r"\bdd\s+.*of=/dev/",        # dd to device
    r"\bmkfs\b",                 # make filesystem
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"\binit\s+0\b",
    r"\b:\(\)\{\s*:\|:&\s*\};\s*:",  # Fork bomb
]


class CommandWhitelistError(Exception):
    """Raised when command is not in whitelist"""
    pass


class CommandWhitelist:
    """
    Layer 2 Security: Validasi perintah berbasis whitelist.
    Hanya perintah dalam COMMAND_WHITELIST yang diizinkan.
    """
    
    def __init__(self, allowed_commands: Optional[set] = None):
        self.allowed_commands = allowed_commands or COMMAND_WHITELIST
        self.blacklist_patterns = COMMAND_BLACKLIST_PATTERNS
    
    def extract_command_prefix(self, command: str) -> str:
        """
        Extract the first word (command name) from a command string.
        Handles edge cases like sudo, paths, etc.
        """
        # Strip leading whitespace
        command = command.strip()
        
        # Handle sudo/doas - get the actual command after it
        if command.startswith(("sudo ", "doas ")):
            parts = command.split(maxsplit=2)
            if len(parts) >= 2:
                return parts[1]
        
        # Get first word
        first_word = command.split()[0] if command.split() else ""
        
        # Extract just the command name (remove path)
        # e.g., /usr/bin/python -> python
        if '/' in first_word or '\\' in first_word:
            first_word = first_word.split('/')[-1].split('\\')[-1]
        
        # Remove .exe extension on Windows
        if first_word.endswith('.exe'):
            first_word = first_word[:-4]
        
        return first_word.lower()
    
    def is_allowed(self, command: str) -> Tuple[bool, str]:
        """
        Check if command is allowed by whitelist.
        Returns (is_allowed, reason)
        """
        if not command or not command.strip():
            return False, "Command kosong"
        
        # Check blacklist patterns first
        for pattern in self.blacklist_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command mengandung pattern berbahaya: {pattern}"
        
        # Extract command prefix
        prefix = self.extract_command_prefix(command)
        
        if not prefix:
            return False, "Tidak dapat mengekstrak command"
        
        # Check whitelist
        if prefix in self.allowed_commands:
            return True, f"Command '{prefix}' diizinkan"
        
        # Check if it's a path to an allowed command
        for allowed in self.allowed_commands:
            if command.startswith(f"./{allowed}") or command.startswith(f"/{allowed}"):
                return True, f"Command '{allowed}' diizinkan (via path)"
        
        return False, f"Command '{prefix}' TIDAK ada dalam whitelist"
    
    def validate(self, command: str, console: Optional[Console] = None) -> str:
        """
        Validate command and raise error if not allowed.
        Returns the command if valid.
        """
        is_allowed, reason = self.is_allowed(command)
        
        if not is_allowed:
            if console:
                console.print(Panel(
                    f"[bold red]LAYER 2: Command Ditolak[/bold red]\n\n"
                    f"[yellow]Command:[/yellow] [cyan]{command}[/cyan]\n\n"
                    f"[yellow]Alasan:[/yellow] {reason}\n\n"
                    f"[dim]Whitelist commands: {', '.join(sorted(self.allowed_commands))}[/dim]",
                    title="Validasi Whitelist",
                    border_style="red",
                ))
            raise CommandWhitelistError(f"Command ditolak: {reason}")
        
        return command


# Global whitelist instance
command_whitelist = CommandWhitelist()
