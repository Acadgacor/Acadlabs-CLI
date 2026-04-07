"""
LAYER 5: CONTAINERIZATION - Eksekusi Terisolasi (Docker)

Menjalankan kode AI di Docker container ephemeral
Kode tidak pernah menyentuh filesystem host secara langsung
"""
import os
import subprocess
import tempfile
from typing import Optional, Tuple, Dict, Any

from rich.console import Console
from rich.panel import Panel


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
