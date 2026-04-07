"""Tool definitions for AI Function Calling (OpenRouter/OpenAI compatible)"""
import os
import subprocess
import fnmatch
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """Schema untuk definisi tool yang akan dikirim ke AI"""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: callable  # Reference ke fungsi Python yang akan dieksekusi


# ============================================
# TOOL FUNCTIONS - Implementasi fungsi lokal
# ============================================

def read_file(path: str, offset: int = 0, limit: int = 100) -> str:
    """
    Membaca isi file dari path yang diberikan.
    
    Args:
        path: Path absolut atau relatif ke file
        offset: Line number mulai (0-indexed)
        limit: Jumlah maksimal baris yang dibaca
    
    Returns:
        Isi file sebagai string
    """
    try:
        # Security: Cegah path traversal
        if ".." in path or path.startswith("/etc") or path.startswith("~"):
            return f"Error: Access denied to path '{path}'"
        
        if not os.path.exists(path):
            return f"Error: File not found: '{path}'"
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # Apply offset and limit
        start = offset
        end = offset + limit if limit > 0 else len(lines)
        selected_lines = lines[start:end]
        
        # Format dengan line numbers
        result = []
        for i, line in enumerate(selected_lines, start=offset + 1):
            result.append(f"{i:4d} | {line.rstrip()}")
        
        return "\n".join(result) if result else "(empty file)"
    
    except Exception as e:
        return f"Error reading file: {e}"


def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """
    Melihat isi direktori.
    
    Args:
        path: Path ke direktori (default: current directory)
        show_hidden: Tampilkan hidden files
    
    Returns:
        Daftar file dan folder
    """
    try:
        # Security check
        if ".." in path:
            return "Error: Path traversal not allowed"
        
        if not os.path.exists(path):
            return f"Error: Directory not found: '{path}'"
        
        if not os.path.isdir(path):
            return f"Error: '{path}' is not a directory"
        
        items = os.listdir(path)
        
        if not show_hidden:
            items = [i for i in items if not i.startswith('.')]
        
        # Sort: folders first, then files
        folders = []
        files = []
        
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                folders.append(f"DIR   {item}/")
            else:
                size = os.path.getsize(full_path)
                files.append(f"FILE  {item} ({size} bytes)")
        
        result = [f"Contents of '{path}':", "-" * 40]
        result.extend(sorted(folders))
        result.extend(sorted(files))
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing directory: {e}"


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


def write_file(path: str, content: str, mode: str = "write") -> str:
    """
    Menulis ke file (DANGEROUS - perlu konfirmasi user).
    
    Args:
        path: Path ke file
        content: Konten yang akan ditulis
        mode: "write" (overwrite) atau "append"
    
    Returns:
        Status operasi
    """
    # WARNING: Fungsi ini harus di-handle dengan konfirmasi user
    
    try:
        # Security: Cek ekstensi berbahaya
        dangerous_exts = ['.exe', '.bat', '.cmd', '.sh', '.ps1']
        if any(path.lower().endswith(ext) for ext in dangerous_exts):
            return f"Error: Writing to '{path}' is blocked for safety"
        
        write_mode = 'w' if mode == "write" else 'a'
        
        # Buat direktori jika belum ada
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "written to" if mode == "write" else "appended to"
        return f"Success: Content {action} '{path}'"
    
    except Exception as e:
        return f"Error writing file: {e}"


def get_current_directory() -> str:
    """Mendapatkan current working directory"""
    return os.getcwd()


# ============================================
# GIT TOOLS - Untuk melihat perubahan project
# ============================================

def git_status() -> str:
    """
    Menjalankan git status untuk melihat file yang dimodifikasi.
    
    Returns:
        Output dari git status
    """
    try:
        # Cek apakah ini git repository
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            return "Info: Ini bukan git repository. Git commands tidak tersedia."
        
        result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        if not result.stdout.strip():
            return "Git status: Working tree clean (tidak ada perubahan)"
        
        # Parse dan format output
        lines = result.stdout.strip().split('\n')
        output = ["Git Status - File yang berubah:", "-" * 40]
        
        for line in lines:
            status = line[:2].strip()
            filepath = line[3:]
            
            # Status codes
            status_map = {
                'M': 'Modified',
                'A': 'Added',
                'D': 'Deleted',
                'R': 'Renamed',
                'C': 'Copied',
                '??': 'Untracked',
                '!!': 'Ignored'
            }
            
            status_text = status_map.get(status, status)
            output.append(f"  [{status}] {status_text}: {filepath}")
        
        
        return '\n'.join(output)
    
    except subprocess.TimeoutExpired:
        return "Error: git status timeout"
    except FileNotFoundError:
        return "Error: git tidak ditemukan. Install git terlebih dahulu."
    except Exception as e:
        return f"Error: {e}"


def git_diff(target: str = "", staged: bool = False) -> str:
    """
    Menjalankan git diff untuk melihat perubahan detail.
    
    Args:
        target: File atau commit spesifik (optional)
        staged: Jika True, tampilkan staged changes
    
    Returns:
        Output dari git diff
    """
    try:
        # Cek apakah ini git repository
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            return "Info: Ini bukan git repository. Git commands tidak tersedia."
        
        
        # Build command
        cmd = ['git', 'diff']
        if staged:
            cmd.append('--staged')
        if target:
            cmd.append(target)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        if not result.stdout.strip():
            return "Git diff: Tidak ada perubahan untuk ditampilkan"
        
        # Truncate jika terlalu panjang
        diff_output = result.stdout
        if len(diff_output) > 3000:
            diff_output = diff_output[:3000] + "\n... (truncated, diff terlalu panjang)"
        
        
        return f"Git Diff:\n{diff_output}"
    
    except subprocess.TimeoutExpired:
        return "Error: git diff timeout"
    except FileNotFoundError:
        return "Error: git tidak ditemukan. Install git terlebih dahulu."
    except Exception as e:
        return f"Error: {e}"


def git_log(limit: int = 10) -> str:
    """
    Menjalankan git log untuk melihat commit history.
    
    Args:
        limit: Jumlah maksimal commit yang ditampilkan
    
    Returns:
        Output dari git log (oneline format)
    """
    try:
        # Cek apakah ini git repository
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            return "Info: Ini bukan git repository. Git commands tidak tersedia."
        
        
        result = subprocess.run(
            ['git', 'log', '--oneline', f'-{limit}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        if not result.stdout.strip():
            return "Git log: Belum ada commit"
        
        lines = result.stdout.strip().split('\n')
        output = [f"Git Log (last {limit} commits):", "-" * 40]
        output.extend(lines)
        
        return '\n'.join(output)
    
    except subprocess.TimeoutExpired:
        return "Error: git log timeout"
    except FileNotFoundError:
        return "Error: git tidak ditemukan. Install git terlebih dahulu."
    except Exception as e:
        return f"Error: {e}"


# ============================================
# PROJECT CONTEXT - Auto-generate project info
# ============================================

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
        context.append("\n📁 Struktur Project:")
        
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
                    connector = "└── " if is_last else "├── "
                    
                    if os.path.isdir(full_path):
                        items.append(f"{prefix}{connector}📁 {entry}/")
                        if depth < max_depth:
                            extension = "    " if is_last else "│   "
                            items.extend(build_tree(full_path, prefix + extension, depth + 1))
                    else:
                        # Show file size
                        size = os.path.getsize(full_path)
                        size_str = f" ({size}b)" if size < 1024 else f" ({size//1024}kb)"
                        items.append(f"{prefix}{connector}📄 {entry}{size_str}")
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
            context.append("\n🔀 Git Info:")
            
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
        context.append("\n🔍 Project Type:")
        
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


def replace_code_block(path: str, old_code: str, new_code: str, replace_all: bool = False) -> str:
    """
    Mengganti blok kode lama dengan blok kode baru (DANGEROUS - perlu konfirmasi user).
    
    Jauh lebih efisien daripada rewrite seluruh file. AI hanya perlu mengirim
    blok kode yang lama dan yang baru, fungsi ini akan mencari dan menggantinya.
    
    Args:
        path: Path ke file yang akan diedit
        old_code: Blok kode yang akan dicari dan diganti (harus exact match)
        new_code: Blok kode baru untuk menggantikan old_code
        replace_all: Jika True, ganti semua kemunculan old_code (default: False)
    
    Returns:
        Status operasi dengan detail perubahan
    """
    # WARNING: Fungsi ini harus di-handle dengan konfirmasi user
    
    try:
        # Security: Cek ekstensi berbahaya
        dangerous_exts = ['.exe', '.bat', '.cmd', '.sh', '.ps1']
        if any(path.lower().endswith(ext) for ext in dangerous_exts):
            return f"Error: Editing '{path}' is blocked for safety"
        
        # Security: Cegah path traversal
        if ".." in path or path.startswith("/etc") or path.startswith("~"):
            return f"Error: Access denied to path '{path}'"
        
        if not os.path.exists(path):
            return f"Error: File not found: '{path}'"
        
        # Baca file
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cari old_code
        if old_code not in content:
            # Berikan hint tentang kemungkinan masalah
            hints = []
            
            # Cek apakah ada whitespace mismatch
            old_lines = old_code.strip().split('\n')
            content_lines = content.strip().split('\n')
            
            # Cari baris pertama yang cocok
            first_line = old_lines[0].strip() if old_lines else ""
            for i, line in enumerate(content_lines):
                if first_line and first_line in line:
                    hints.append(f"Hint: Baris pertama old_code ditemukan di sekitar line {i+1}, mungkin ada whitespace/indentation mismatch")
                    break
            
            # Cek ukuran
            if len(old_code) < 10:
                hints.append("Hint: old_code terlalu pendek, gunakan blok kode yang lebih besar untuk keunikan")
            
            hint_msg = "\n".join(hints) if hints else "Pastikan old_code exactly match dengan isi file (termasuk whitespace/indentation)"
            
            return f"Error: old_code tidak ditemukan di file.\n{hint_msg}"
        
        
        # Hitung jumlah kemunculan
        occurrences = content.count(old_code)
        
        if occurrences > 1 and not replace_all:
            return (
                f"Error: old_code ditemukan {occurrences} kali di file. "
                f"Gunakan replace_all=True untuk mengganti semua kemunculan, "
                f"atau perbesar blok kode untuk membuatnya unik."
            )
        
        
        # Lakukan replacement
        if replace_all:
            new_content = content.replace(old_code, new_code)
            count = occurrences
        else:
            new_content = content.replace(old_code, new_code, 1)
            count = 1
        
        # Tulis kembali file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Hitung statistik perubahan
        old_lines = old_code.count('\n') + 1
        new_lines = new_code.count('\n') + 1
        
        return (
            f"Success: Replaced {count} occurrence(s) in '{path}'\n"
            f"  - Old: {old_lines} lines\n"
            f"  - New: {new_lines} lines\n"
            f"  - File size: {len(content)} -> {len(new_content)} bytes"
        )
    
    except Exception as e:
        return f"Error editing file: {e}"


# ============================================
# TOOL DEFINITIONS - Schema untuk OpenRouter
# ============================================

TOOLS_REGISTRY: List[ToolDefinition] = [
    ToolDefinition(
        name="read_file",
        description="Membaca isi file. Gunakan untuk melihat kode atau konfigurasi.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path ke file yang akan dibaca"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number mulai (0-indexed, default 0)",
                    "default": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "Jumlah baris maksimal yang dibaca (default 100)",
                    "default": 100
                }
            },
            "required": ["path"]
        },
        function=read_file
    ),
    
    ToolDefinition(
        name="list_directory",
        description="Melihat isi direktori. Gunakan untuk eksplorasi struktur project.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path ke direktori (default: current directory)",
                    "default": "."
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Tampilkan hidden files",
                    "default": False
                }
            },
            "required": []
        },
        function=list_directory
    ),
    
    ToolDefinition(
        name="run_terminal_command",
        description="Menjalankan shell command. PERLU KONFIRMASI USER. Gunakan dengan hati-hati.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command shell yang akan dijalankan"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout dalam detik (default 30)",
                    "default": 30
                }
            },
            "required": ["command"]
        },
        function=run_terminal_command
    ),
    
    ToolDefinition(
        name="search_code",
        description="Mencari string/pattern di dalam file project.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "String yang dicari"
                },
                "path": {
                    "type": "string",
                    "description": "Direktori pencarian (default: current)",
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Pattern file, misal *.py (default: *)",
                    "default": "*"
                }
            },
            "required": ["query"]
        },
        function=search_code
    ),
    
    ToolDefinition(
        name="write_file",
        description="Menulis ke file. PERLU KONFIRMASI USER. Gunakan untuk membuat atau mengubah file.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path ke file"
                },
                "content": {
                    "type": "string",
                    "description": "Konten yang akan ditulis"
                },
                "mode": {
                    "type": "string",
                    "enum": ["write", "append"],
                    "description": "Mode: 'write' (overwrite) atau 'append'",
                    "default": "write"
                }
            },
            "required": ["path", "content"]
        },
        function=write_file
    ),
    
    ToolDefinition(
        name="get_current_directory",
        description="Mendapatkan current working directory.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        function=get_current_directory
    ),
    
    ToolDefinition(
        name="replace_code_block",
        description=(
            "Mengganti blok kode lama dengan baru. JAUH LEBIH EFISIEN daripada write_file. "
            "PERLU KONFIRMASI USER. Kirim old_code (exact match) dan new_code, "
            "fungsi ini akan mencari dan menggantinya. Gunakan untuk refactoring/editing file besar."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path ke file yang akan diedit"
                },
                "old_code": {
                    "type": "string",
                    "description": "Blok kode yang akan dicari dan diganti (harus exact match termasuk whitespace/indentation)"
                },
                "new_code": {
                    "type": "string",
                    "description": "Blok kode baru untuk menggantikan old_code"
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Jika True, ganti semua kemunculan old_code (default: False)",
                    "default": False
                }
            },
            "required": ["path", "old_code", "new_code"]
        },
        function=replace_code_block
    ),
    
    # Git Tools
    ToolDefinition(
        name="git_status",
        description="Melihat file yang dimodifikasi di git. Gunakan untuk memahami apa yang user kerjakan sebelumnya.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        function=git_status
    ),
    
    ToolDefinition(
        name="git_diff",
        description="Melihat detail perubahan kode di git. Gunakan untuk memahami modifikasi spesifik yang user buat.",
        parameters={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "File spesifik untuk diff (optional)",
                    "default": ""
                },
                "staged": {
                    "type": "boolean",
                    "description": "Tampilkan staged changes",
                    "default": False
                }
            },
            "required": []
        },
        function=git_diff
    ),
    
    ToolDefinition(
        name="git_log",
        description="Melihat commit history. Gunakan untuk memahami riwayat perubahan project.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Jumlah commit yang ditampilkan (default 10)",
                    "default": 10
                }
            },
            "required": []
        },
        function=git_log
    ),
    
    # Project Context
    ToolDefinition(
        name="get_project_context",
        description="Mendapatkan konteks project (struktur folder, git info, project type). Gunakan di awal untuk memahami project.",
        parameters={
            "type": "object",
            "properties": {
                "max_depth": {
                    "type": "integer",
                    "description": "Kedalaman tree struktur (default 2)",
                    "default": 2
                }
            },
            "required": []
        },
        function=get_project_context
    ),
]


def get_tools_schema() -> List[Dict[str, Any]]:
    """
    Mengambil schema tools dalam format OpenAI/OpenRouter function calling.
    
    Returns:
        List of tool schemas untuk dikirim ke API
    """
    schemas = []
    for tool in TOOLS_REGISTRY:
        schemas.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        })
    return schemas


def get_tool_by_name(name: str) -> Optional[ToolDefinition]:
    """
    Mencari tool berdasarkan nama.
    
    Args:
        name: Nama tool
    
    Returns:
        ToolDefinition atau None jika tidak ditemukan
    """
    for tool in TOOLS_REGISTRY:
        if tool.name == name:
            return tool
    return None


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """
    Mengeksekusi tool berdasarkan nama dan argumen.
    
    Args:
        name: Nama tool
        arguments: Dictionary argumen untuk tool
    
    Returns:
        Hasil eksekusi tool sebagai string
    """
    tool = get_tool_by_name(name)
    
    if not tool:
        return f"Error: Unknown tool '{name}'"
    
    try:
        result = tool.function(**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing tool '{name}': {e}"


# ============================================
# CATEGORIZE TOOLS BY SAFETY LEVEL
# ============================================

SAFE_TOOLS = {"read_file", "list_directory", "search_code", "get_current_directory", "git_status", "git_diff", "git_log", "get_project_context"}
DANGEROUS_TOOLS = {"run_terminal_command", "write_file", "replace_code_block"}

def is_dangerous_tool(name: str) -> bool:
    """Cek apakah tool memerlukan konfirmasi user"""
    return name in DANGEROUS_TOOLS
