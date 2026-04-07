"""Token module - Token estimation and management"""

from acadlabs_cli.core.token.estimator import (
    CHARS_PER_TOKEN,
    MODEL_CONTEXT_LIMITS,
    WARNING_THRESHOLD,
    CRITICAL_THRESHOLD,
    DANGER_THRESHOLD,
    estimate_tokens,
    estimate_message_tokens,
    estimate_history_tokens,
    estimate_api_tokens,
)

from acadlabs_cli.core.token.manager import (
    TokenUsage,
    TokenManager,
    create_token_manager,
    token_manager,
    check_and_prompt_clear,
)

__all__ = [
    # Constants
    "CHARS_PER_TOKEN",
    "MODEL_CONTEXT_LIMITS",
    "WARNING_THRESHOLD",
    "CRITICAL_THRESHOLD",
    "DANGER_THRESHOLD",
    # Estimation functions
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_history_tokens",
    "estimate_api_tokens",
    # Manager classes
    "TokenUsage",
    "TokenManager",
    "create_token_manager",
    "token_manager",
    "check_and_prompt_clear",
]
