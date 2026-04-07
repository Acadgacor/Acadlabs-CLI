"""Tools module - File operations, Git operations, System operations, and Registry"""

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

from acadlabs_cli.tools.registry import (
    ToolDefinition,
    TOOLS_REGISTRY,
    get_tools_schema,
    get_tool_by_name,
    execute_tool,
    SAFE_TOOLS,
    DANGEROUS_TOOLS,
    is_dangerous_tool,
)

__all__ = [
    # File operations
    "read_file",
    "write_file",
    "replace_code_block",
    "list_directory",
    
    # Git operations
    "git_status",
    "git_diff",
    "git_log",
    
    # System operations
    "run_terminal_command",
    "search_code",
    "get_current_directory",
    "get_project_context",
    
    # Registry
    "ToolDefinition",
    "TOOLS_REGISTRY",
    "get_tools_schema",
    "get_tool_by_name",
    "execute_tool",
    "SAFE_TOOLS",
    "DANGEROUS_TOOLS",
    "is_dangerous_tool",
]
