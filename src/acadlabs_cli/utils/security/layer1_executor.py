"""
LAYER 1: EXECUTION WRAPPERS - Human-in-the-Loop

Semua fungsi di bawah ini WAJIB melewati konfirmasi y/n sebelum eksekusi
Gunakan fungsi-fungsi ini sebagai pengganti subprocess/os/shutil langsung
"""
import subprocess
import shutil
from typing import Optional, Callable
from functools import wraps

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

# Import from other security layers
from acadlabs_cli.utils.security.layer2_whitelist import (
    CommandWhitelist,
    CommandWhitelistError,
    command_whitelist,
)
from acadlabs_cli.utils.security.layer3_parser import (
    CommandParser,
    CommandInjectionError,
    command_parser,
)
from acadlabs_cli.utils.security.layer4_pathlock import (
    PathLocker,
    PathLockError,
    path_locker,
)
from acadlabs_cli.utils.security.layer5_docker import (
    DockerExecutor,
    ContainerizationError,
    docker_executor,
)


class SecurityViolationError(Exception):
    """Raised when user rejects a dangerous action"""
    pass


class SecureExecutor:
    """
    Wrapper untuk semua operasi berbahaya dengan Human-in-the-Loop.
    
    LAYER 5 (Containerization) - opsional untuk eksekusi kode
    LAYER 4 (Path Locking) - untuk operasi file
    LAYER 3 (Anti-Injection) - untuk command
    LAYER 2 (Whitelist) - untuk validasi command
    LAYER 1 (Konfirmasi y/n) - untuk semua operasi
    
    Setiap operasi yang memodifikasi sistem WAJIB melewati konfirmasi.
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        whitelist: Optional[CommandWhitelist] = None,
        parser: Optional[CommandParser] = None,
        path_locker: Optional[PathLocker] = None,
        docker_executor: Optional[DockerExecutor] = None
    ):
        self.console = console or Console()
        self.whitelist = whitelist or command_whitelist
        self.parser = parser or command_parser
        self.path_locker = path_locker or path_locker
        self.docker_executor = docker_executor or docker_executor
    
    def _confirm(self, operation: str, details: str, show_preview: bool = True) -> bool:
        """
        Generic confirmation prompt.
        Returns True if user approves, False otherwise.
        """
        self.console.print()
        self.console.print(Panel(
            f"[bold red]PERINGATAN: Operasi Berbahaya[/bold red]\n\n"
            f"[yellow]Operasi:[/yellow] {operation}\n"
            f"[yellow]Detail:[/yellow]\n{details}",
            title="Konfirmasi Keamanan (y/n)",
            border_style="yellow",
        ))
        
        return Confirm.ask(
            "[bold red]Izinkan operasi ini?[/bold red]",
            default=False
        )
    
    # ====================
    # SUBPROCESS WRAPPERS
    # ====================
    
    def run_command(self, command: str, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute shell command with confirmation.
        Pengganti subprocess.run() dengan konfirmasi.
        
        Flow:
        1. Layer 3: Anti-injection (parse & deteksi injection)
        2. Layer 2: Validasi whitelist (auto-reject jika tidak diizinkan)
        3. Layer 1: Konfirmasi y/n dari user
        4. Eksekusi dengan shell=False (aman dari injection)
        """
        # LAYER 3: Anti-injection - Parse command safely
        cmd_list = self.parser.parse_safe(command, self.console)
        
        # LAYER 2: Whitelist validation
        self.whitelist.validate(command, self.console)
        
        # LAYER 1: Human confirmation
        if not self._confirm("Menjalankan command sistem", f"[cyan]{command}[/cyan]"):
            raise SecurityViolationError(f"Command ditolak oleh user: {command}")
        
        self.console.print(f"[green]Menjalankan (shell=False, aman):[/green] {command}")
        # LAYER 3: Gunakan shell=False untuk mencegah injection
        return subprocess.run(cmd_list, shell=False, **kwargs)
    
    def run_command_safe(self, command: list, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute command (list form, safer) with confirmation.
        Pengganti subprocess.run() dengan list args.
        
        Flow:
        1. Layer 3: Anti-injection (sudah dalam bentuk list, aman)
        2. Layer 2: Validasi whitelist
        3. Layer 1: Konfirmasi y/n
        4. Eksekusi dengan shell=False
        """
        cmd_str = ' '.join(command)
        
        # LAYER 3: Verify tidak ada injection dalam args
        for arg in command:
            has_injection, detected = self.parser.detect_injection(arg)
            if has_injection:
                self.console.print(Panel(
                    f"[bold red]LAYER 3: Injection dalam argumen![/bold red]\n\n"
                    f"[yellow]Argumen:[/yellow] [cyan]{arg}[/cyan]\n"
                    f"[yellow]Terdeteksi:[/yellow] {detected}",
                    title="Anti-Injection Protection",
                    border_style="red",
                ))
                raise CommandInjectionError(f"Injection dalam argumen: {detected}")
        
        
        # LAYER 2: Whitelist validation
        self.whitelist.validate(cmd_str, self.console)
        
        # LAYER 1: Human confirmation
        if not self._confirm("Menjalankan command", f"[cyan]{cmd_str}[/cyan]"):
            raise SecurityViolationError(f"Command ditolak oleh user: {cmd_str}")
        
        self.console.print(f"[green]Menjalankan (shell=False, aman):[/green] {cmd_str}")
        # LAYER 3: shell=False sudah default untuk list args
        return subprocess.run(command, shell=False, **kwargs)
    
    # ====================
    # FILE OPERATION WRAPPERS
    # ====================
    
    def write_file(self, filepath: str, content: str, mode: str = 'w') -> int:
        """
        Write to file with confirmation.
        Pengganti open(filepath, 'w').write() dengan konfirmasi.
        
        Flow:
        1. Layer 4: Path locking (pastikan dalam project)
        2. Layer 1: Konfirmasi y/n
        3. Eksekusi
        """
        # LAYER 4: Path validation
        safe_path = self.path_locker.validate(filepath, operation="write")
        
        # Show preview of content
        preview = content[:500] + "..." if len(content) > 500 else content
        
        # LAYER 1: Human confirmation
        if not self._confirm(
            f"Menulis ke file ({mode})",
            f"[cyan]{safe_path}[/cyan]\n\n[dim]Preview:[/dim]\n{preview}"
        ):
            raise SecurityViolationError(f"File write ditolak oleh user: {filepath}")
        
        self.console.print(f"[green]Menulis ke:[/green] {safe_path}")
        with open(safe_path, mode, encoding='utf-8') as f:
            return f.write(content)
    
    
    def delete_file(self, filepath: str) -> None:
        """
        Delete file with confirmation.
        Pengganti os.remove() dengan konfirmasi.
        
        Flow:
        1. Layer 4: Path locking
        2. Layer 1: Konfirmasi y/n
        3. Eksekusi
        """
        import os
        
        # LAYER 4: Path validation
        safe_path = self.path_locker.validate(filepath, operation="delete")
        
        # LAYER 1: Human confirmation
        if not self._confirm("Menghapus file", f"[red]{safe_path}[/red]"):
            raise SecurityViolationError(f"File delete ditolak oleh user: {filepath}")
        
        self.console.print(f"[green]Menghapus:[/green] {safe_path}")
        os.remove(safe_path)
    
    
    def delete_directory(self, dirpath: str) -> None:
        """
        Delete directory with confirmation.
        Pengganti shutil.rmtree() dengan konfirmasi.
        
        Flow:
        1. Layer 4: Path locking
        2. Layer 1: Konfirmasi y/n
        3. Eksekusi
        """
        # LAYER 4: Path validation
        safe_path = self.path_locker.validate(dirpath, operation="delete directory")
        
        # LAYER 1: Human confirmation
        if not self._confirm("Menghapus direktori", f"[red]{safe_path}[/red]"):
            raise SecurityViolationError(f"Directory delete ditolak oleh user: {dirpath}")
        
        self.console.print(f"[green]Menghapus direktori:[/green] {safe_path}")
        shutil.rmtree(safe_path)
    
    
    def create_directory(self, dirpath: str) -> None:
        """
        Create directory with confirmation.
        Pengganti os.makedirs() dengan konfirmasi.
        
        Flow:
        1. Layer 4: Path locking
        2. Layer 1: Konfirmasi y/n
        3. Eksekusi
        """
        import os
        
        # LAYER 4: Path validation
        safe_path = self.path_locker.validate(dirpath, operation="create directory")
        
        # LAYER 1: Human confirmation
        if not self._confirm("Membuat direktori", f"[cyan]{safe_path}[/cyan]"):
            raise SecurityViolationError(f"Directory create ditolak oleh user: {dirpath}")
        
        self.console.print(f"[green]Membuat direktori:[/green] {safe_path}")
        os.makedirs(safe_path, exist_ok=True)
    
    
    # ====================
    # GIT OPERATION WRAPPERS
    # ====================
    
    def execute_in_container(self, code: str, language: str = "python") -> tuple:
        """
        Execute code in isolated Docker container (Layer 5).
        
        Flow:
        1. Layer 1: Konfirmasi y/n
        2. Layer 5: Eksekusi di container terisolasi
        """
        # LAYER 1: Human confirmation
        if not self._confirm(
            "Menjalankan kode di container terisolasi",
            f"[cyan]Language:[/cyan] {language}\n[dim]{code[:200]}...[/dim]"
        ):
            raise SecurityViolationError("Container execution ditolak oleh user")
        
        self.console.print("[green]Menjalankan di container terisolasi[/green]")
        return self.docker_executor.execute_code(code, language)
    
    def git_operation(self, command: str) -> subprocess.CompletedProcess:
        """
        Execute git command with confirmation.
        Khusus untuk operasi git yang berbahaya.
        """
        if not self._confirm("Operasi Git", f"[cyan]git {command}[/cyan]"):
            raise SecurityViolationError(f"Git operation ditolak oleh user: git {command}")
        
        self.console.print(f"[green]Git:[/green] {command}")
        return subprocess.run(f"git {command}", shell=True)


# ============================================================================
# DECORATOR FOR CUSTOM DANGEROUS FUNCTIONS
# ============================================================================

def require_confirmation(description: str = "operasi berbahaya"):
    """
    Decorator untuk fungsi yang memerlukan konfirmasi.
    
    Usage:
        @require_confirmation("mengubah config")
        def update_config(key, value):
            # ... kode yang berbahaya ...
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            console = Console()
            console.print()
            console.print(Panel(
                f"[bold red]Konfirmasi Diperlukan[/bold red]\n\n"
                f"[yellow]Fungsi:[/yellow] {func.__name__}\n"
                f"[yellow]Deskripsi:[/yellow] {description}",
                title="Human-in-the-Loop",
                border_style="yellow",
            ))
            
            if not Confirm.ask("[bold red]Lanjutkan?[/bold red]", default=False):
                raise SecurityViolationError(f"Fungsi {func.__name__} ditolak oleh user")
            
            console.print(f"[green]Menjalankan:[/green] {func.__name__}")
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# GLOBAL INSTANCE - Gunakan ini untuk semua operasi
# ============================================================================

secure_executor = SecureExecutor()

# Convenience aliases untuk import langsung
run_command = secure_executor.run_command
run_command_safe = secure_executor.run_command_safe
write_file = secure_executor.write_file
delete_file = secure_executor.delete_file
delete_directory = secure_executor.delete_directory
create_directory = secure_executor.create_directory
git_operation = secure_executor.git_operation
