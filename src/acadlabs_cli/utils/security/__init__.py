"""Security layers module - 5 Layer Security System"""

from acadlabs_cli.utils.security.layer2_whitelist import (
    CommandWhitelist,
    CommandWhitelistError,
    command_whitelist,
    COMMAND_WHITELIST,
    COMMAND_BLACKLIST_PATTERNS,
)

from acadlabs_cli.utils.security.layer3_parser import (
    CommandParser,
    CommandInjectionError,
    command_parser,
    INJECTION_CHARACTERS,
    INJECTION_PATTERNS,
)

from acadlabs_cli.utils.security.layer4_pathlock import (
    PathLocker,
    PathLockError,
    path_locker,
    FORBIDDEN_PATHS,
    PATH_TRAVERSAL_PATTERNS,
)

from acadlabs_cli.utils.security.layer5_docker import (
    DockerExecutor,
    ContainerizationError,
    docker_executor,
    DEFAULT_EXECUTION_IMAGE,
    DEFAULT_CONTAINER_TIMEOUT,
)

from acadlabs_cli.utils.security.layer1_executor import (
    SecureExecutor,
    SecurityViolationError,
    secure_executor,
    require_confirmation,
    run_command,
    run_command_safe,
    write_file,
    delete_file,
    delete_directory,
    create_directory,
    git_operation,
)

__all__ = [
    # Layer 2: Whitelist
    "CommandWhitelist",
    "CommandWhitelistError",
    "command_whitelist",
    "COMMAND_WHITELIST",
    "COMMAND_BLACKLIST_PATTERNS",
    
    # Layer 3: Anti-Injection
    "CommandParser",
    "CommandInjectionError",
    "command_parser",
    "INJECTION_CHARACTERS",
    "INJECTION_PATTERNS",
    
    # Layer 4: Path Locking
    "PathLocker",
    "PathLockError",
    "path_locker",
    "FORBIDDEN_PATHS",
    "PATH_TRAVERSAL_PATTERNS",
    
    # Layer 5: Containerization
    "DockerExecutor",
    "ContainerizationError",
    "docker_executor",
    "DEFAULT_EXECUTION_IMAGE",
    "DEFAULT_CONTAINER_TIMEOUT",
    
    # Layer 1: Secure Executor
    "SecureExecutor",
    "SecurityViolationError",
    "secure_executor",
    "require_confirmation",
    
    # Convenience functions
    "run_command",
    "run_command_safe",
    "write_file",
    "delete_file",
    "delete_directory",
    "create_directory",
    "git_operation",
]
