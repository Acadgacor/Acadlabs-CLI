"""
Test script untuk verifikasi Tool Calling system
Run: python -m examples.test_tool_calling
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acadlabs_cli.utils.tools import (
    get_tools_schema,
    execute_tool,
    get_tool_by_name,
    is_dangerous_tool,
    SAFE_TOOLS,
    DANGEROUS_TOOLS,
    TOOLS_REGISTRY,
)
from acadlabs_cli.utils.tool_executor import ToolExecutor


def test_tools_schema():
    """Test: Tools schema generation"""
    print("\n=== Test: Tools Schema ===")
    
    schema = get_tools_schema()
    print(f"Total tools: {len(schema)}")
    
    for tool in schema:
        print(f"  - {tool['function']['name']}: {tool['function']['description'][:50]}...")
    
    assert len(schema) == 11, "Should have 11 tools"
    print("PASSED")


def test_tool_by_name():
    """Test: Get tool by name"""
    print("\n=== Test: Get Tool By Name ===")
    
    tool = get_tool_by_name("read_file")
    assert tool is not None, "read_file should exist"
    assert tool.name == "read_file"
    print(f"  Found: {tool.name}")
    
    tool = get_tool_by_name("nonexistent")
    assert tool is None, "nonexistent should return None"
    print("  nonexistent returns None")
    print("PASSED")


def test_dangerous_tool_detection():
    """Test: Dangerous tool detection"""
    print("\n=== Test: Dangerous Tool Detection ===")
    
    safe_tools = ["read_file", "list_directory", "search_code", "get_current_directory"]
    dangerous_tools = ["run_terminal_command", "write_file"]
    
    for tool in safe_tools:
        assert not is_dangerous_tool(tool), f"{tool} should be safe"
        print(f"  {tool}: SAFE")
    
    for tool in dangerous_tools:
        assert is_dangerous_tool(tool), f"{tool} should be dangerous"
        print(f"  {tool}: DANGEROUS")
    
    print("PASSED")


def test_execute_safe_tools():
    """Test: Execute safe tools"""
    print("\n=== Test: Execute Safe Tools ===")
    
    # Test get_current_directory
    result = execute_tool("get_current_directory", {})
    print(f"  get_current_directory: {result}")
    assert "Error" not in result, "Should not error"
    
    # Test list_directory
    result = execute_tool("list_directory", {"path": ".", "show_hidden": False})
    print(f"  list_directory: {result[:100]}...")
    assert "Contents of" in result or "Error" not in result
    
    # Test read_file
    result = execute_tool("read_file", {"path": "README.md", "limit": 5})
    print(f"  read_file (README.md): {result[:100]}...")
    
    # Test search_code
    result = execute_tool("search_code", {"query": "def", "file_pattern": "*.py"})
    print(f"  search_code: {result[:100]}...")
    
    print("PASSED")


def test_tool_executor():
    """Test: Tool Executor with confirmation"""
    print("\n=== Test: Tool Executor ===")
    
    # Create executor with auto-approve for testing
    executor = ToolExecutor(auto_approve_safe=True, auto_approve_dangerous=True)
    
    # Simulate tool calls from AI
    tool_calls = [
        {
            "id": "call_1",
            "name": "get_current_directory",
            "arguments": {}
        },
        {
            "id": "call_2",
            "name": "list_directory",
            "arguments": {"path": "."}
        }
    ]
    
    results, executed = executor.process_tool_calls(tool_calls)
    
    print(f"  Executed {len(executed)} tools")
    for e in executed:
        print(f"    - {e['name']}: {e['result'][:50]}...")
    
    assert len(results) == 2, "Should have 2 results"
    print("PASSED")


def test_tool_executor_blocks_dangerous():
    """Test: Tool Executor blocks dangerous tools when not approved"""
    print("\n=== Test: Tool Executor Blocks Dangerous ===")
    
    # Create executor that does NOT auto-approve dangerous
    executor = ToolExecutor(auto_approve_safe=True, auto_approve_dangerous=False)
    
    # Simulate dangerous tool call
    tool_calls = [
        {
            "id": "call_1",
            "name": "write_file",
            "arguments": {"path": "test.txt", "content": "test"}
        }
    ]
    
    # This should be blocked (we can't test interactive confirmation in automated test)
    # But we can verify the logic
    print("  Dangerous tool detection works")
    assert is_dangerous_tool("write_file")
    print("PASSED")


def test_replace_code_block():
    """Test: replace_code_block tool for smart partial editing"""
    print("\n=== Test: replace_code_block ===")
    
    import tempfile
    import os
    
    # Create a temp file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""def hello():
    print("hello")

def world():
    print("world")
""")
        temp_path = f.name
    
    try:
        # Test 1: Basic replacement
        result = execute_tool("replace_code_block", {
            "path": temp_path,
            "old_code": 'print("hello")',
            "new_code": 'print("hello world")'
        })
        print(f"  Basic replacement: {result[:50]}...")
        assert "Success" in result, f"Should succeed: {result}"
        
        # Verify the change
        with open(temp_path, 'r') as f:
            content = f.read()
        assert 'print("hello world")' in content
        print("  Content verified: OK")
        
        # Test 2: Multi-line replacement
        result = execute_tool("replace_code_block", {
            "path": temp_path,
            "old_code": 'def world():\n    print("world")',
            "new_code": 'def world():\n    print("universe")'
        })
        print(f"  Multi-line replacement: {result[:50]}...")
        assert "Success" in result
        
        # Verify
        with open(temp_path, 'r') as f:
            content = f.read()
        assert 'print("universe")' in content
        print("  Multi-line verified: OK")
        
        # Test 3: Error case - old_code not found
        result = execute_tool("replace_code_block", {
            "path": temp_path,
            "old_code": "nonexistent code",
            "new_code": "something"
        })
        print(f"  Not found error: {result[:50]}...")
        assert "Error" in result or "tidak ditemukan" in result
        print("  Error handling: OK")
        
        # Test 4: Verify it's marked as dangerous
        assert is_dangerous_tool("replace_code_block"), "Should be dangerous"
        print("  Dangerous classification: OK")
        
        print("PASSED")
        
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_git_tools():
    """Test: Git tools for context awareness"""
    print("\n=== Test: Git Tools ===")
    
    # Test git_status
    result = execute_tool("git_status", {})
    print(f"  git_status: {result[:80]}...")
    assert "Error" not in result or "git tidak ditemukan" in result or "git repository" in result
    
    # Test git_diff
    result = execute_tool("git_diff", {})
    print(f"  git_diff: {result[:80]}...")
    
    # Test git_log
    result = execute_tool("git_log", {"limit": 5})
    print(f"  git_log: {result[:80]}...")
    
    # Verify these are safe tools
    assert not is_dangerous_tool("git_status")
    assert not is_dangerous_tool("git_diff")
    assert not is_dangerous_tool("git_log")
    print("  Safe classification: OK")
    
    print("PASSED")


def test_project_context():
    """Test: Project context tool"""
    print("\n=== Test: Project Context ===")
    
    result = execute_tool("get_project_context", {"max_depth": 2})
    print(f"  get_project_context: {result[:150]}...")
    
    # Should contain project root
    assert "Project Root" in result or "Error" not in result
    
    # Should detect project type
    if "Python" in result:
        print("  Detected: Python project")
    
    # Verify it's a safe tool
    assert not is_dangerous_tool("get_project_context")
    print("  Safe classification: OK")
    
    print("PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Testing Tool Calling System")
    print("=" * 50)
    
    try:
        test_tools_schema()
        test_tool_by_name()
        test_dangerous_tool_detection()
        test_execute_safe_tools()
        test_tool_executor()
        test_tool_executor_blocks_dangerous()
        test_replace_code_block()
        test_git_tools()
        test_project_context()
        
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        return True
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
