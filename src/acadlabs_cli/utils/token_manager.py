"""
Token & Cost Management System

Menghitung dan memonitor penggunaan token untuk mencegah biaya tak terduga.
Memberikan warning ketika context window mendekati batas dan opsi untuk clear context.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()


# ============================================
# TOKEN ESTIMATION
# ============================================

# Approximation: ~4 characters per token for English text
# For code, it's roughly similar but can vary
CHARS_PER_TOKEN = 4

# Model context limits (common models)
MODEL_CONTEXT_LIMITS = {
    # OpenAI models
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-3.5-turbo": 16385,
    
    # Anthropic models
    "claude-2": 100000,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3.5-sonnet": 200000,
    
    # OpenRouter free models
    "astepfun/step-3.5-flash:free": 128000,
    "meta-llama/llama-3.1-8b-instruct:free": 128000,
    "google/gemma-2-9b-it:free": 8192,
    
    # Default fallback
    "default": 128000,
}

# Warning thresholds (percentage of context limit)
WARNING_THRESHOLD = 0.4    # 40% - First warning
CRITICAL_THRESHOLD = 0.6   # 60% - Critical warning
DANGER_THRESHOLD = 0.8     # 80% - Danger zone


def estimate_tokens(text: str) -> int:
    """
    Estimasi jumlah token dari text.
    
    Menggunakan approximation ~4 chars per token.
    Untuk estimasi lebih akurat, bisa menggunakan tiktoken library.
    
    Args:
        text: Text yang akan dihitung token-nya
    
    Returns:
        Estimasi jumlah token
    """
    if not text:
        return 0
    
    # Count words and characters
    # Code typically has more tokens due to symbols
    char_count = len(text)
    word_count = len(text.split())
    
    # Estimate based on characters (more accurate for code)
    token_estimate = char_count // CHARS_PER_TOKEN
    
    # Adjust for code (more symbols = more tokens)
    symbol_count = len(re.findall(r'[{}()\[\];:,.<>?/\\|!@#$%^&*+=\-_~`]', text))
    symbol_tokens = symbol_count // 2  # Symbols often are separate tokens
    
    return token_estimate + symbol_tokens


def estimate_message_tokens(message: Dict) -> int:
    """
    Estimasi token dari satu message (termasuk role overhead).
    
    Args:
        message: Dict dengan 'role' dan 'content' (atau fields lain)
    
    Returns:
        Estimasi jumlah token
    """
    # Base overhead for message structure
    overhead = 4  # role, content keys, etc.
    
    content = message.get("content", "")
    if content is None:
        content = ""
    
    # Handle different content types
    if isinstance(content, str):
        content_tokens = estimate_tokens(content)
    elif isinstance(content, list):
        # For multimodal messages
        content_tokens = sum(
            estimate_tokens(item.get("text", "")) 
            for item in content 
            if isinstance(item, dict)
        )
    else:
        content_tokens = 0
    
    # Tool calls add extra tokens
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        for tc in tool_calls:
            content_tokens += estimate_tokens(tc.get("function", {}).get("name", ""))
            content_tokens += estimate_tokens(tc.get("function", {}).get("arguments", ""))
    
    # Tool call ID
    if "tool_call_id" in message:
        overhead += 2
    
    return content_tokens + overhead


def estimate_history_tokens(history: List[Dict]) -> int:
    """
    Estimasi total token dari chat history.
    
    Args:
        history: List of message dicts
    
    Returns:
        Total estimasi token
    """
    total = 0
    for msg in history:
        total += estimate_message_tokens(msg)
    return total


# ============================================
# TOKEN MANAGER CLASS
# ============================================

@dataclass
class TokenUsage:
    """Tracking penggunaan token"""
    prompt_tokens: int = 0      # Tokens di prompt/context
    completion_tokens: int = 0  # Tokens di response AI
    total_tokens: int = 0       # Total keseluruhan
    
    # Tracking per iterasi
    iterations: List[Dict] = field(default_factory=list)
    
    def add_iteration(self, prompt_tokens: int, completion_tokens: int, tool_calls: int = 0):
        """Tambah data iterasi baru"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        
        self.iterations.append({
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tool_calls": tool_calls,
            "cumulative": self.total_tokens
        })


class TokenManager:
    """
    Manager untuk tracking dan warning token usage.
    
    Features:
    - Track token usage per iteration
    - Warn when approaching context limit
    - Estimate cost based on model pricing
    - Provide option to clear context
    """
    
    def __init__(
        self,
        model: str = "astepfun/step-3.5-flash:free",
        warning_threshold: float = WARNING_THRESHOLD,
        critical_threshold: float = CRITICAL_THRESHOLD,
        danger_threshold: float = DANGER_THRESHOLD,
        auto_warn: bool = True
    ):
        self.model = model
        self.context_limit = MODEL_CONTEXT_LIMITS.get(model, MODEL_CONTEXT_LIMITS["default"])
        
        self.warning_threshold = int(self.context_limit * warning_threshold)
        self.critical_threshold = int(self.context_limit * critical_threshold)
        self.danger_threshold = int(self.context_limit * danger_threshold)
        
        self.auto_warn = auto_warn
        self.usage = TokenUsage()
        
        # Track warnings given
        self.warnings_given = {
            "warning": False,
            "critical": False,
            "danger": False
        }
        
        # Cost estimation (per 1M tokens)
        # These are approximate prices, update based on actual model
        self.pricing = self._get_model_pricing(model)
    
    def _get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for model (per 1M tokens)"""
        # Approximate pricing - update with actual values
        pricing_map = {
            "gpt-4": {"prompt": 30.0, "completion": 60.0},
            "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
            "gpt-4o": {"prompt": 5.0, "completion": 15.0},
            "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
            "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
            "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
            "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
            "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
            "claude-3.5-sonnet": {"prompt": 3.0, "completion": 15.0},
            # Free models
            "astepfun/step-3.5-flash:free": {"prompt": 0.0, "completion": 0.0},
            "meta-llama/llama-3.1-8b-instruct:free": {"prompt": 0.0, "completion": 0.0},
        }
        return pricing_map.get(model, {"prompt": 1.0, "completion": 2.0})
    
    def estimate_cost(self) -> float:
        """Estimasi biaya dalam USD"""
        prompt_cost = (self.usage.prompt_tokens / 1_000_000) * self.pricing["prompt"]
        completion_cost = (self.usage.completion_tokens / 1_000_000) * self.pricing["completion"]
        return prompt_cost + completion_cost
    
    def check_history(self, history: List[Dict]) -> int:
        """
        Check token count dari history.
        
        Returns:
            Total token count
        """
        return estimate_history_tokens(history)
    
    def check_and_warn(self, history: List[Dict]) -> Tuple[bool, str]:
        """
        Check token usage dan berikan warning jika perlu.
        
        Returns:
            (should_warn, warning_message)
        """
        token_count = self.check_history(history)
        usage_percent = (token_count / self.context_limit) * 100
        
        # Check thresholds
        if token_count >= self.danger_threshold and not self.warnings_given["danger"]:
            self.warnings_given["danger"] = True
            msg = self._build_warning_message(
                token_count, usage_percent, "DANGER"
            )
            return True, msg
        
        elif token_count >= self.critical_threshold and not self.warnings_given["critical"]:
            self.warnings_given["critical"] = True
            msg = self._build_warning_message(
                token_count, usage_percent, "CRITICAL"
            )
            return True, msg
        
        elif token_count >= self.warning_threshold and not self.warnings_given["warning"]:
            self.warnings_given["warning"] = True
            msg = self._build_warning_message(
                token_count, usage_percent, "WARNING"
            )
            return True, msg
        
        return False, ""
    
    def _build_warning_message(
        self, 
        token_count: int, 
        usage_percent: float, 
        level: str
    ) -> str:
        """Build warning message"""
        colors = {
            "WARNING": "yellow",
            "CRITICAL": "orange",
            "DANGER": "red"
        }
        color = colors.get(level, "yellow")
        
        cost = self.estimate_cost()
        
        msg = f"""
[{color}]Context Window {level}![/{color}]

Token Usage: {token_count:,} / {self.context_limit:,} ({usage_percent:.1f}%)
Estimated Cost: ${cost:.4f} USD

Biaya prompt akan mulai mahal karena context yang panjang.
Pertimbangkan untuk:
1. Clear context (hapus chat history)
2. Mulai session baru
3. Fokus pada task spesifik

Ketik 'clear' untuk menghapus context atau 'continue' untuk melanjutkan.
"""
        return msg
    
    def display_warning(self, token_count: int, usage_percent: float, level: str):
        """Display warning ke console"""
        colors = {
            "WARNING": "yellow",
            "CRITICAL": "orange3",
            "DANGER": "red"
        }
        color = colors.get(level, "yellow")
        
        cost = self.estimate_cost()
        
        console.print(Panel(
            f"[bold {color}]Context Window {level}![/bold {color}]\n\n"
            f"Token Usage: [bold]{token_count:,}[/bold] / {self.context_limit:,} ({usage_percent:.1f}%)\n"
            f"Estimated Cost: [bold]${cost:.4f} USD[/bold]\n\n"
            f"[dim]Biaya prompt akan mulai mahal karena context yang panjang.[/dim]\n"
            f"[dim]Pertimbangkan untuk clear context atau mulai session baru.[/dim]",
            title=f"[{color}]Token Warning[/{color}]",
            border_style=color
        ))
    
    def prompt_clear_context(self) -> bool:
        """
        Tanya user apakah ingin clear context.
        
        Returns:
            True jika user ingin clear, False jika lanjut
        """
        console.print("\n[yellow]Options:[/yellow]")
        console.print("  [cyan]clear[/cyan] - Hapus chat history dan mulai fresh")
        console.print("  [cyan]continue[/cyan] - Lanjutkan dengan context saat ini")
        console.print("  [cyan]status[/cyan] - Lihat detail token usage")
        
        choice = Prompt.ask(
            "\n[bold]Pilihanmu[/bold]",
            choices=["clear", "continue", "status"],
            default="continue"
        )
        
        if choice == "clear":
            return True
        elif choice == "status":
            self.display_status()
            return self.prompt_clear_context()  # Ask again
        else:
            return False
    
    def display_status(self):
        """Display status token usage"""
        cost = self.estimate_cost()
        usage_percent = (self.usage.total_tokens / self.context_limit) * 100
        
        console.print(Panel(
            f"[bold]Token Usage Summary[/bold]\n\n"
            f"Model: {self.model}\n"
            f"Context Limit: {self.context_limit:,} tokens\n\n"
            f"Prompt Tokens: {self.usage.prompt_tokens:,}\n"
            f"Completion Tokens: {self.usage.completion_tokens:,}\n"
            f"Total Tokens: {self.usage.total_tokens:,} ({usage_percent:.1f}%)\n\n"
            f"Estimated Cost: ${cost:.4f} USD\n"
            f"Iterations: {len(self.usage.iterations)}",
            title="Token Status",
            border_style="cyan"
        ))
    
    def add_usage(self, prompt_tokens: int, completion_tokens: int, tool_calls: int = 0):
        """Add token usage dari satu iterasi"""
        self.usage.add_iteration(prompt_tokens, completion_tokens, tool_calls)
    
    def reset(self):
        """Reset usage tracking"""
        self.usage = TokenUsage()
        self.warnings_given = {
            "warning": False,
            "critical": False,
            "danger": False
        }
    
    def get_status_summary(self) -> str:
        """Get short status summary untuk display"""
        cost = self.estimate_cost()
        return (
            f"Tokens: {self.usage.total_tokens:,} | "
            f"Cost: ${cost:.4f} | "
            f"Iterations: {len(self.usage.iterations)}"
        )


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def create_token_manager(model: str = None) -> TokenManager:
    """Factory function untuk membuat TokenManager"""
    if model is None:
        # Get from config or use default
        try:
            from acadlabs_cli.client.openrouter import openrouter_client
            model = openrouter_client.default_model
        except:
            model = "astepfun/step-3.5-flash:free"
    
    return TokenManager(model=model)


# Default instance
token_manager = TokenManager()


# ============================================
# INTEGRATION HELPERS
# ============================================

def check_and_prompt_clear(
    history: List[Dict],
    manager: TokenManager = None
) -> Tuple[bool, List[Dict]]:
    """
    Check token usage dan prompt user untuk clear jika perlu.
    
    Args:
        history: Chat history
        manager: TokenManager instance (optional)
    
    Returns:
        (should_clear, new_history)
        - should_clear: True jika user pilih clear
        - new_history: History baru (kosong jika clear, sama jika tidak)
    """
    if manager is None:
        manager = token_manager
    
    should_warn, msg = manager.check_and_warn(history)
    
    if should_warn:
        token_count = manager.check_history(history)
        usage_percent = (token_count / manager.context_limit) * 100
        
        # Determine level
        if token_count >= manager.danger_threshold:
            level = "DANGER"
        elif token_count >= manager.critical_threshold:
            level = "CRITICAL"
        else:
            level = "WARNING"
        
        manager.display_warning(token_count, usage_percent, level)
        
        if manager.prompt_clear_context():
            manager.reset()
            return True, []
    
    return False, history


def estimate_api_tokens(messages: List[Dict]) -> int:
    """
    Estimasi total tokens yang akan dikirim ke API.
    
    Berguna untuk pre-check sebelum API call.
    """
    total = 0
    
    # System prompt overhead
    total += 20  # Approximate
    
    # Messages
    total += estimate_history_tokens(messages)
    
    # Tools schema overhead (if using tools)
    total += 500  # Approximate for tools schema
    
    return total
