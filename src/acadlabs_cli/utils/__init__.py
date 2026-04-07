"""Utils module - 5 Layer Security System (Refactored)"""

# Import from action_detection module
from acadlabs_cli.utils.action_detection import (
    # Detectors
    ActionDetector,
    ActionConfirmator,
    action_confirmator,
    create_action_confirmator,
    DANGEROUS_PATTERNS,
    ACTION_DESCRIPTIONS,
)

# Import from security module (all layers)
from acadlabs_cli.utils.security import (
    # Layer 5: Containerization
    DockerExecutor,
    ContainerizationError,
    docker_executor,
    DEFAULT_EXECUTION_IMAGE,
    DEFAULT_CONTAINER_TIMEOUT,
    
    # Layer 4: Path Locking
    PathLocker,
    PathLockError,
    path_locker,
    FORBIDDEN_PATHS,
    PATH_TRAVERSAL_PATTERNS,
    
    # Layer 3: Anti-Injection
    CommandParser,
    CommandInjectionError,
    command_parser,
    INJECTION_CHARACTERS,
    INJECTION_PATTERNS,
    
    # Layer 2: Whitelist Validation
    CommandWhitelist,
    CommandWhitelistError,
    command_whitelist,
    COMMAND_WHITELIST,
    COMMAND_BLACKLIST_PATTERNS,
    
    # Layer 1: Secure Executor (Human-in-the-Loop)
    SecureExecutor,
    SecurityViolationError,
    secure_executor,
    
    # Convenience functions (semua layer -> Eksekusi)
    run_command,
    run_command_safe,
    write_file,
    delete_file,
    delete_directory,
    create_directory,
    git_operation,
    
    # Decorator for custom dangerous functions
    require_confirmation,
)

# Import from token_manager module
from acadlabs_cli.utils.token_manager import (
    TokenManager,
    TokenUsage,
    create_token_manager,
    estimate_tokens,
    estimate_message_tokens,
    estimate_history_tokens,
    estimate_api_tokens,
    check_and_prompt_clear,
    token_manager,
    MODEL_CONTEXT_LIMITS,
    WARNING_THRESHOLD,
    CRITICAL_THRESHOLD,
    DANGER_THRESHOLD,
)

__all__ = [
    # Detectors
    "ActionDetector",
    "ActionConfirmator",
    "action_confirmator",
    "create_action_confirmator",
    "DANGEROUS_PATTERNS",
    "ACTION_DESCRIPTIONS",
    
    # Layer 5: Containerization
    "DockerExecutor",
    "ContainerizationError",
    "docker_executor",
    "DEFAULT_EXECUTION_IMAGE",
    "DEFAULT_CONTAINER_TIMEOUT",
    
    # Layer 4: Path Locking
    "PathLocker",
    "PathLockError",
    "path_locker",
    "FORBIDDEN_PATHS",
    "PATH_TRAVERSAL_PATTERNS",
    
    # Layer 3: Anti-Injection
    "CommandParser",
    "CommandInjectionError",
    "command_parser",
    "INJECTION_CHARACTERS",
    "INJECTION_PATTERNS",
    
    # Layer 2: Whitelist
    "CommandWhitelist",
    "CommandWhitelistError",
    "command_whitelist",
    "COMMAND_WHITELIST",
    "COMMAND_BLACKLIST_PATTERNS",
    
    # Layer 1: Secure Executor
    "SecureExecutor",
    "SecurityViolationError",
    "secure_executor",
    
    # Convenience functions
    "run_command",
    "run_command_safe",
    "write_file",
    "delete_file",
    "delete_directory",
    "create_directory",
    "git_operation",
    
    # Decorator
    "require_confirmation",
    
    # Token Manager
    "TokenManager",
    "TokenUsage",
    "create_token_manager",
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_history_tokens",
    "estimate_api_tokens",
    "check_and_prompt_clear",
    "token_manager",
    "MODEL_CONTEXT_LIMITS",
    "WARNING_THRESHOLD",
    "CRITICAL_THRESHOLD",
    "DANGER_THRESHOLD",
]
