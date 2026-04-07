"""Utils module - 5 Layer Security System"""

from acadlabs_cli.utils.actions import (
    # Detectors
    ActionDetector,
    ActionConfirmator,
    
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

__all__ = [
    # Detectors
    "ActionDetector",
    "ActionConfirmator",
    
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
]
