"""
Token Estimation Functions

Fungsi-fungsi untuk estimasi jumlah token tanpa menggunakan tiktoken.
Menggunakan approximation ~4 chars per token.
"""
import re
from typing import List, Dict


# ============================================
# CONSTANTS
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


# ============================================
# ESTIMATION FUNCTIONS
# ============================================

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
