"""System Operations - Tools for terminal commands, search, and project context"""
import os
import subprocess
import fnmatch
from typing import List


def run_terminal_command(command: str, timeout: int = 30) -> str:
    """
    Menjalankan terminal command (DANGEROUS - perlu konfirmasi user).
    
    Args:
        command: Command shell yang akan dijalankan
        timeout: Timeout dalam detik
    
    Returns:
        Output dari command
    """
    # WARNING: Fungsi ini harus di-handle dengan konfirmasi user
    # di layer ActionConfirmator sebelum dieksekusi
    
    # Blacklist commands
    BLACKLIST = ["rm -rf", "format", "del /", "mkfs", "dd if="]
    for bl in BLACKLIST:
        if bl in command.lower():
            return f"Error: Command '{command}' is blocked for safety"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if result.returncode != 0:
            output.append(f"Exit code: {result.returncode}")
        
        return "\n".join(output) if output else "(no output)"
    
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as e:
        return f"Error executing command: {e}"


def search_code(query: str, path: str = ".", file_pattern: str = "*") -> str:
    """
    Mencari kode/pattern di dalam file.
    
    Args:
        query: String atau pattern yang dicari
        path: Direktori tempat pencarian
        file_pattern: Pattern file (e.g., "*.py", "*.js")
    
    Returns:
        Hasil pencarian dengan file dan line numbers
    """
    try:
        results = []
        count = 0
        max_results = 50
        
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for filename in files:
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue
                
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                results.append(f"{filepath}:{line_num}: {line.strip()}")
                                count += 1
                                
                                if count >= max_results:
                                    return "\n".join(results) + f"\n\n... (truncated, {max_results} max)"
                except:
                    continue
        
        if not results:
            return f"No matches found for '{query}'"
        
        return "\n".join(results)
    
    except Exception as e:
        return f"Error searching: {e}"


def get_current_directory() -> str:
    """Mendapatkan current working directory"""
    return os.getcwd()


def get_project_context(max_depth: int = 2) -> str:
    """
    Mendapatkan konteks project secara otomatis (struktur folder, info git, dll).
    
    Args:
        max_depth: Kedalaman maksimal untuk tree struktur
    
    Returns:
        Ringkasan konteks project
    """
    try:
        cwd = os.getcwd()
        context = []
        
        # 1. Project root
        context.append(f"Project Root: {cwd}")
        context.append("-" * 50)
        
        # 2. Struktur folder (tree-like)
        context.append("\n Struktur Project:")
        
        def build_tree(path: str, prefix: str = "", depth: int = 0) -> List[str]:
            if depth > max_depth:
                return []
            
            items = []
            try:
                entries = sorted(os.listdir(path))
                # Filter out hidden dan common ignore patterns
                ignore_patterns = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 
                                   '.idea', '.vscode', '*.egg-info', 'dist', 'build', '.tox'}
                entries = [e for e in entries if not any(
                    fnmatch.fnmatch(e, pat) or e in ignore_patterns 
                    for pat in ignore_patterns
                )]
                
                for i, entry in enumerate(entries):
                    full_path = os.path.join(path, entry)
                    is_last = i == len(entries) - 1
                    connector = "    " if is_last else "   "
                    
                    if os.path.isdir(full_path):
                        items.append(f"{prefix}{connector} {entry}/")
                        if depth < max_depth:
                            extension = "    " if is_last else "   "
                            items.extend(build_tree(full_path, prefix + extension, depth + 1))
                    else:
                        # Show file size
                        size = os.path.getsize(full_path)
                        size_str = f" ({size}b)" if size < 1024 else f" ({size//1024}kb)"
                        items.append(f"{prefix}{connector} {entry}{size_str}")
            except PermissionError:
                pass
            
            return items
        
        tree = build_tree(cwd)
        context.extend(tree[:50])  # Limit output
        if len(tree) > 50:
            context.append(f"... dan {len(tree) - 50} item lainnya")
        
        # 3. Git info jika ada
        git_dir = os.path.join(cwd, '.git')
        if os.path.exists(git_dir):
            context.append("\n Git Info:")
            
            # Current branch
            try:
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True, text=True, timeout=5
                )
                branch = result.stdout.strip() or "(unknown)"
                context.append(f"  Branch: {branch}")
            except:
                pass
            
            # Status summary
            try:
                result = subprocess.run(
                    ['git', 'status', '--short'],
                    capture_output=True, text=True, timeout=5
                )
                changes = len([l for l in result.stdout.strip().split('\n') if l])
                if changes > 0:
                    context.append(f"  Modified files: {changes}")
                else:
                    context.append("  Status: Clean")
            except:
                pass
        
        
        # 4. Detect project type
        context.append("\n Project Type:")
        
        if os.path.exists(os.path.join(cwd, 'pyproject.toml')):
            context.append("  Python (pyproject.toml)")
        if os.path.exists(os.path.join(cwd, 'requirements.txt')):
            context.append("  Python (requirements.txt)")
        if os.path.exists(os.path.join(cwd, 'package.json')):
            context.append("  Node.js (package.json)")
        if os.path.exists(os.path.join(cwd, 'Cargo.toml')):
            context.append("  Rust (Cargo.toml)")
        if os.path.exists(os.path.join(cwd, 'go.mod')):
            context.append("  Go (go.mod)")
        
        return '\n'.join(context)
    
    except Exception as e:
        return f"Error getting project context: {e}"
