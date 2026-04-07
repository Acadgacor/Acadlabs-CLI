"""Human-in-the-Loop action confirmation system"""
import re
import subprocess
import shutil
import os
import shlex
from typing import Optional, Tuple, List, Callable
from functools import wraps
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# ============================================================================
# LAYER 2: COMMAND WHITELIST - Validasi Perintah
# ============================================================================
# Lebih aman dari blacklist: HANYA perintah dalam whitelist yang diizinkan
# Semua perintah di luar whitelist ditolak OTOMATIS tanpa konfirmasi
# ============================================================================

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

# ============================================================================
# LAYER 3: ANTI-INJECTION - Isolasi Parameter Eksekusi
# ============================================================================
# Mencegah command injection dengan:
# 1. shell=False (OS tidak interpret karakter spesial)
# 2. Parse command string menjadi list aman
# 3. Deteksi dan blokir karakter injeksi
# ============================================================================

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


class CommandWhitelistError(Exception):
    """Raised when command is not in whitelist"""
    pass


class CommandInjectionError(Exception):
    """Raised when command injection is detected (Layer 3)"""
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


# ============================================================================
# LAYER 4: PATH LOCKING - Pembatasan Scope Direktori
# ============================================================================
# AI tidak bisa mengakses path di luar direktori project (cwd)
# Mencegah akses ke folder sistem atau file sensitif
# ============================================================================

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


# ============================================================================
# LAYER 5: CONTAINERIZATION - Eksekusi Terisolasi (Docker)
# ============================================================================
# Menjalankan kode AI di Docker container ephemeral
# Kode tidak pernah menyentuh filesystem host secara langsung
# ============================================================================

# Default Docker image untuk eksekusi kode
DEFAULT_EXECUTION_IMAGE = "python:3.11-slim"

# Timeout untuk eksekusi container (detik)
DEFAULT_CONTAINER_TIMEOUT = 30


class ContainerizationError(Exception):
    """Raised when containerization fails (Layer 5)"""
    pass


class DockerExecutor:
    """
    Layer 5 Security: Eksekusi kode di Docker container terisolasi.
    
    Kode AI dijalankan di container ephemeral yang:
    - Di-spawn saat dibutuhkan
    - Tidak memiliki akses ke filesystem host
    - Dihancurkan setelah eksekusi (ephemeral)
    - Memiliki timeout untuk mencegah infinite loop
    """
    
    def __init__(
        self, 
        image: str = DEFAULT_EXECUTION_IMAGE,
        timeout: int = DEFAULT_CONTAINER_TIMEOUT,
        console: Optional[Console] = None
    ):
        self.image = image
        self.timeout = timeout
        self.console = console or Console()
        self._docker_available = None
    
    def is_docker_available(self) -> bool:
        """
        Check if Docker is installed and running.
        """
        if self._docker_available is not None:
            return self._docker_available
        
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            self._docker_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._docker_available = False
        
        return self._docker_available
    
    def create_container_spec(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Create Docker container specification.
        """
        if language == "python":
            return {
                "Image": self.image,
                "Cmd": ["python", "-c", code],
                "HostConfig": {
                    "Memory": 256 * 1024 * 1024,  # 256MB limit
                    "CpuQuota": 50000,  # 50% CPU
                    "NetworkMode": "none",  # No network access
                    "AutoRemove": True,  # Ephemeral
                },
                "Env": ["PYTHONUNBUFFERED=1"],
            }
        else:
            raise ContainerizationError(f"Language '{language}' not supported yet")
    
    def execute_code(self, code: str, language: str = "python") -> Tuple[int, str, str]:
        """
        Execute code in isolated Docker container.
        
        Returns (exit_code, stdout, stderr)
        """
        # Check Docker availability
        if not self.is_docker_available():
            self.console.print(Panel(
                f"[bold red]LAYER 5: Docker tidak tersedia![/bold red]\n\n"
                f"[yellow]Status:[/yellow] Docker tidak terinstall atau tidak running\n\n"
                f"[dim]Install Docker untuk mengaktifkan eksekusi terisolasi[/dim]",
                title="Containerization",
                border_style="yellow",
            ))
            raise ContainerizationError("Docker tidak tersedia. Install Docker untuk Layer 5.")
        
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix=f'.{language}', 
            delete=False
        ) as f:
            f.write(code)
            code_file = f.name
        
        try:
            # Build container name
            container_name = f"acadlabs_exec_{os.getpid()}_{id(code)}"
            
            self.console.print(f"[cyan]Spawning container:[/cyan] {container_name}")
            
            # Run container with mounted code
            result = subprocess.run(
                [
                    "docker", "run",
                    "--name", container_name,
                    "--rm",  # Auto-remove after execution
                    "--network", "none",  # No network
                    "--memory", "256m",  # Memory limit
                    "--cpus", "0.5",  # CPU limit
                    "--timeout", str(self.timeout),
                    "-v", f"{code_file}:/code/exec.{language}:ro",
                    self.image,
                    language, f"/code/exec.{language}"
                ] if language == "python" else [
                    "docker", "run", "--rm", "--network", "none",
                    "--memory", "256m", "--timeout", str(self.timeout),
                    self.image, language, "-c", code
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout + 5  # Extra buffer
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            raise ContainerizationError(f"Eksekusi timeout setelah {self.timeout} detik")
        except Exception as e:
            raise ContainerizationError(f"Gagal menjalankan container: {e}")
        finally:
            # Cleanup temp file
            try:
                os.unlink(code_file)
            except:
                pass
    
    def execute_python(self, code: str) -> Tuple[int, str, str]:
        """
        Execute Python code in container.
        Convenience method.
        """
        return self.execute_code(code, language="python")


# Global docker executor instance
docker_executor = DockerExecutor()


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


# ============================================================================
# EXECUTION WRAPPERS - Layer 1 Security (Human-in-the-Loop)
# ============================================================================
# Semua fungsi di bawah ini WAJIB melewati konfirmasi y/n sebelum eksekusi
# Gunakan fungsi-fungsi ini sebagai pengganti subprocess/os/shutil langsung
# ============================================================================

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
        self.path_locker = path_locker or globals()['path_locker']
        self.docker_executor = docker_executor or globals()['docker_executor']
    
    def _confirm(self, operation: str, details: str, show_preview: bool = True) -> bool:
        """
        Generic confirmation prompt.
        Returns True if user approves, False otherwise.
        """
        self.console.print()
        self.console.print(Panel(
            f"[bold red]⚠️  PERINGATAN: Operasi Berbahaya[/bold red]\n\n"
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
        
        self.console.print(f"[green]✓ Menjalankan (shell=False, aman):[/green] {command}")
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
        
        self.console.print(f"[green]✓ Menjalankan (shell=False, aman):[/green] {cmd_str}")
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
        
        self.console.print(f"[green]✓ Menulis ke:[/green] {safe_path}")
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
        # LAYER 4: Path validation
        safe_path = self.path_locker.validate(filepath, operation="delete")
        
        # LAYER 1: Human confirmation
        if not self._confirm("Menghapus file", f"[red]{safe_path}[/red]"):
            raise SecurityViolationError(f"File delete ditolak oleh user: {filepath}")
        
        self.console.print(f"[green]✓ Menghapus:[/green] {safe_path}")
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
        
        self.console.print(f"[green]✓ Menghapus direktori:[/green] {safe_path}")
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
        # LAYER 4: Path validation
        safe_path = self.path_locker.validate(dirpath, operation="create directory")
        
        # LAYER 1: Human confirmation
        if not self._confirm("Membuat direktori", f"[cyan]{safe_path}[/cyan]"):
            raise SecurityViolationError(f"Directory create ditolak oleh user: {dirpath}")
        
        self.console.print(f"[green]✓ Membuat direktori:[/green] {safe_path}")
        os.makedirs(safe_path, exist_ok=True)
    
    
    # ====================
    # GIT OPERATION WRAPPERS
    # ====================
    
    def execute_in_container(self, code: str, language: str = "python") -> Tuple[int, str, str]:
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
        
        self.console.print("[green]✓ Menjalankan di container terisolasi[/green]")
        return self.docker_executor.execute_code(code, language)
    
    def git_operation(self, command: str) -> subprocess.CompletedProcess:
        """
        Execute git command with confirmation.
        Khusus untuk operasi git yang berbahaya.
        """
        if not self._confirm("Operasi Git", f"[cyan]git {command}[/cyan]"):
            raise SecurityViolationError(f"Git operation ditolak oleh user: git {command}")
        
        self.console.print(f"[green]✓ Git:[/green] {command}")
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
                f"[bold red]⚠️  Konfirmasi Diperlukan[/bold red]\n\n"
                f"[yellow]Fungsi:[/yellow] {func.__name__}\n"
                f"[yellow]Deskripsi:[/yellow] {description}",
                title="Human-in-the-Loop",
                border_style="yellow",
            ))
            
            if not Confirm.ask("[bold red]Lanjutkan?[/bold red]", default=False):
                raise SecurityViolationError(f"Fungsi {func.__name__} ditolak oleh user")
            
            console.print(f"[green]✓ Menjalankan:[/green] {func.__name__}")
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


def create_action_confirmator() -> ActionConfirmator:
    """Factory function to create ActionConfirmator instance"""
    return ActionConfirmator()


# Global instance for easy import
action_confirmator = ActionConfirmator()
