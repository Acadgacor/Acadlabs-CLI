"""Tool Registry - Central registry for all tools with schemas"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import all tool functions
from acadlabs_cli.tools.file_ops import (
    read_file,
    write_file,
    replace_code_block,
    list_directory,
)

from acadlabs_cli.tools.git_ops import (
    git_status,
    git_diff,
    git_log,
)

from acadlabs_cli.tools.sys_ops import (
    run_terminal_command,
    search_code,
    get_current_directory,
    get_project_context,
)


@dataclass
class ToolDefinition:
    """Schema untuk definisi tool yang akan dikirim ke AI"""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: callable  # Reference ke fungsi Python yang akan dieksekusi


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
