"""
Agentic Loop Configuration and State

Classes untuk konfigurasi dan state tracking agentic loop.
"""
from typing import List
from dataclasses import dataclass, field
from enum import Enum


class LoopStatus(Enum):
    """Status dari agentic loop iteration"""
    CONTINUE = "continue"      # AI masih bekerja
    COMPLETED = "completed"    # AI menyatakan selesai
    ERROR = "error"            # Terjadi error
    BLOCKED = "blocked"        # User memblokir aksi
    MAX_ITERATIONS = "max"     # Mencapai batas iterasi


@dataclass
class LoopState:
    """State tracking untuk agentic loop"""
    iteration: int = 0
    total_tools_called: int = 0
    tools_this_iteration: int = 0
    errors: List[str] = field(default_factory=list)
    blocked_actions: List[str] = field(default_factory=list)
    last_response: str = ""
    is_complete: bool = False
    # Token tracking
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class AgenticConfig:
    """Konfigurasi untuk agentic loop"""
    max_iterations: int = 15           # Maksimal iterasi untuk mencegah infinite loop
    max_tools_per_iteration: int = 5   # Maksimal tool calls per iterasi
    auto_approve_safe: bool = True     # Auto-approve safe tools
    auto_approve_dangerous: bool = False  # Selalu minta konfirmasi untuk dangerous tools
    show_thinking: bool = True         # Tampilkan proses "berpikir"
    verbose: bool = True               # Tampilkan detail eksekusi
    # Token management
    token_warning_threshold: int = 50000  # Warning ketika tokens mencapai threshold
    enable_token_warnings: bool = True   # Aktifkan warning token
