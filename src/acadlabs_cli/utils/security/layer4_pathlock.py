"""
LAYER 4: PATH LOCKING - Pembatasan Scope Direktori

AI tidak bisa mengakses path di luar direktori project (cwd)
Mencegah akses ke folder sistem atau file sensitif
"""
import re
import os
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel


# Path yang TIDAK PERNAH diizinkan (sistem sensitif)
FORBIDDEN_PATHS = {
    # Unix system paths
    "/", "/etc", "/var", "/usr", "/bin", "/sbin", "/lib", "/lib64",
    "/root", "/home", "/boot", "/dev", "/proc", "/sys",
    
    # Windows system paths
    "C:\\", "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
    "C:\\Users", "C:\\ProgramData",
    
    # Common sensitive files
    "/etc/passwd", "/etc/shadow", "/etc/hosts",
    "~/.ssh", "~/.gnupg", "~/.bash_history",
    ".env", ".gitconfig", ".npmrc", ".pypirc",
}

# Patterns untuk deteksi path traversal
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",           # ../
    r"\.\.\\",          # ..\
    r"~/",              # ~/ (home directory)
    r"/etc/",           # Unix system
    r"/var/",           # Unix system
    r"/root/",          # Unix root
    r"C:\\Windows",     # Windows system
    r"C:\\Users",       # Windows users
]


class PathLockError(Exception):
    """Raised when path access is denied (Layer 4)"""
    pass


class PathLocker:
    """
    Layer 4 Security: Pembatasan scope direktori.
    
    AI hanya boleh mengakses file/folder di dalam project directory (cwd).
    Path traversal (../), absolute root paths, dan sensitive paths diblokir.
    """
    
    def __init__(self, project_root: Optional[str] = None, console: Optional[Console] = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.console = console or Console()
        self.forbidden_paths = FORBIDDEN_PATHS
        self.traversal_patterns = PATH_TRAVERSAL_PATTERNS
    
    def normalize_path(self, path: str) -> Path:
        """
        Normalize path and resolve to absolute.
        """
        # Expand user (~) but don't allow it
        if path.startswith("~"):
            raise PathLockError("Akses ke home directory tidak diizinkan")
        
        # Convert to Path and resolve
        try:
            p = Path(path)
            if not p.is_absolute():
                p = self.project_root / p
            return p.resolve()
        except Exception as e:
            raise PathLockError(f"Path tidak valid: {path} - {e}")
    
    def is_path_traversal(self, path: str) -> bool:
        """
        Check if path contains traversal patterns.
        """
        for pattern in self.traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False
    
    def is_forbidden(self, path: str) -> Tuple[bool, str]:
        """
        Check if path is in forbidden list.
        Returns (is_forbidden, reason)
        """
        normalized = str(self.normalize_path(path))
        
        for forbidden in self.forbidden_paths:
            forbidden_expanded = str(Path(forbidden).expanduser().resolve())
            if normalized.startswith(forbidden_expanded) or normalized == forbidden_expanded:
                return True, f"Path sistem sensitif: {forbidden}"
        
        return False, ""
    
    def is_within_project(self, path: str) -> bool:
        """
        Check if path is within project root.
        """
        try:
            normalized = self.normalize_path(path)
            return str(normalized).startswith(str(self.project_root))
        except PathLockError:
            return False
    
    def validate(self, path: str, operation: str = "access") -> Path:
        """
        Validate path for operation.
        
        Raises PathLockError if path is not allowed.
        Returns normalized Path if valid.
        """
        # Step 1: Check for path traversal
        if self.is_path_traversal(path):
            self.console.print(Panel(
                f"[bold red]LAYER 4: Path Traversal Terdeteksi![/bold red]\n\n"
                f"[yellow]Path:[/yellow] [cyan]{path}[/cyan]\n\n"
                f"[yellow]Operasi:[/yellow] {operation}\n\n"
                f"[dim]Path traversal (../), home directory (~), dan sistem path tidak diizinkan[/dim]",
                title="Path Lock Protection",
                border_style="red",
            ))
            raise PathLockError(f"Path traversal terdeteksi: {path}")
        
        # Step 2: Check forbidden paths
        is_forbidden, reason = self.is_forbidden(path)
        if is_forbidden:
            self.console.print(Panel(
                f"[bold red]LAYER 4: Path Sistem Diblokir![/bold red]\n\n"
                f"[yellow]Path:[/yellow] [cyan]{path}[/cyan]\n\n"
                f"[yellow]Alasan:[/yellow] {reason}",
                title="Path Lock Protection",
                border_style="red",
            ))
            raise PathLockError(reason)
        
        # Step 3: Check within project
        if not self.is_within_project(path):
            self.console.print(Panel(
                f"[bold red]LAYER 4: Akses di luar Project![/bold red]\n\n"
                f"[yellow]Path:[/yellow] [cyan]{path}[/cyan]\n\n"
                f"[yellow]Project root:[/yellow] [green]{self.project_root}[/green]\n\n"
                f"[dim]AI hanya boleh mengakses file di dalam project directory[/dim]",
                title="Path Lock Protection",
                border_style="red",
            ))
            raise PathLockError(f"Path di luar project root: {path}")
        
        return self.normalize_path(path)
    
    def get_safe_path(self, path: str) -> str:
        """
        Get validated safe path string.
        """
        return str(self.validate(path))


# Global path locker instance
path_locker = PathLocker()
