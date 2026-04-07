"""
Test script untuk verifikasi Agentic Loop system
Run: python -m examples.test_agentic_loop
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acadlabs_cli.utils.agentic_loop import (
    AgenticLoop,
    AgenticConfig,
    LoopState,
    LoopStatus,
    create_agentic_loop,
)
from acadlabs_cli.utils.tools import (
    get_tools_schema,
    execute_tool,
    is_dangerous_tool,
    TOOLS_REGISTRY,
)


def test_agentic_config():
    """Test: AgenticConfig creation"""
    print("\n=== Test: Agentic Config ===")
    
    config = AgenticConfig(
        max_iterations=10,
        max_tools_per_iteration=3,
        auto_approve_safe=True,
        auto_approve_dangerous=False,
        verbose=False
    )
    
    assert config.max_iterations == 10
    assert config.max_tools_per_iteration == 3
    assert config.auto_approve_safe == True
    assert config.auto_approve_dangerous == False
    print("  Config created successfully")
    print("PASSED")


def test_loop_state():
    """Test: LoopState tracking"""
    print("\n=== Test: Loop State ===")
    
    state = LoopState()
    assert state.iteration == 0
    assert state.total_tools_called == 0
    assert state.is_complete == False
    assert len(state.errors) == 0
    
    # Simulate state changes
    state.iteration = 1
    state.total_tools_called = 3
    state.errors.append("test error")
    
    assert state.iteration == 1
    assert state.total_tools_called == 3
    assert len(state.errors) == 1
    print("  State tracking works correctly")
    print("PASSED")


def test_agentic_loop_creation():
    """Test: AgenticLoop instance creation"""
    print("\n=== Test: Agentic Loop Creation ===")
    
    # Create with default config
    loop = AgenticLoop()
    assert loop.config.max_iterations == 15
    assert loop.config.auto_approve_safe == True
    print("  Default config applied")
    
    # Create with custom config
    config = AgenticConfig(max_iterations=5, verbose=False)
    loop = AgenticLoop(config=config)
    assert loop.config.max_iterations == 5
    print("  Custom config applied")
    
    # Create via factory function
    loop = create_agentic_loop(max_iterations=20)
    assert loop.config.max_iterations == 20
    print("  Factory function works")
    
    print("PASSED")


def test_security_integration():
    """Test: Integration with security layers"""
    print("\n=== Test: Security Integration ===")
    
    loop = AgenticLoop()
    
    # Test dangerous tool detection
    assert loop.is_dangerous_tool_fn("write_file") == True
    assert loop.is_dangerous_tool_fn("run_terminal_command") == True
    assert loop.is_dangerous_tool_fn("read_file") == False
    assert loop.is_dangerous_tool_fn("list_directory") == False
    print("  Dangerous tool detection works")
    
    # Test safe tool execution (auto-approved)
    result, approved = loop._execute_dangerous_tool("read_file", {"path": "README.md", "limit": 5})
    # read_file is safe, so it uses different path
    print(f"  Safe tool execution: approved={approved}")
    
    print("PASSED")


def test_observation_message_building():
    """Test: Building observation message for AI"""
    print("\n=== Test: Observation Message Building ===")
    
    loop = AgenticLoop()
    
    tool_calls = [
        {"id": "1", "name": "read_file", "arguments": {"path": "test.py"}},
        {"id": "2", "name": "search_code", "arguments": {"query": "def"}}
    ]
    
    tool_results = [
        "1 | print('hello')",
        "test.py:1: def hello():"
    ]
    
    message = loop._build_observation_message(tool_calls, tool_results)
    
    assert "read_file" in message
    assert "search_code" in message
    assert "print('hello')" in message
    print("  Observation message built correctly")
    print(f"  Message preview: {message[:100]}...")
    
    print("PASSED")


def test_max_iterations_protection():
    """Test: Max iterations protection against infinite loops"""
    print("\n=== Test: Max Iterations Protection ===")
    
    config = AgenticConfig(
        max_iterations=3,
        auto_approve_safe=True,
        verbose=False
    )
    loop = AgenticLoop(config=config)
    
    # Mock ask_ai function that always returns tool calls
    call_count = 0
    
    def mock_ask_ai(message, history, tools):
        nonlocal call_count
        call_count += 1
        return f"Response {call_count}", [
            {"id": f"call_{call_count}", "name": "get_current_directory", "arguments": {}}
        ]
    
    # Run the loop
    final_response, state, log = loop.run(
        user_message="test",
        ask_ai_func=mock_ask_ai,
        history=[],
        tools_schema=get_tools_schema()
    )
    
    # Should stop at max_iterations
    assert state.iteration <= config.max_iterations + 1  # +1 for the check
    print(f"  Stopped at iteration {state.iteration} (max: {config.max_iterations})")
    print(f"  Total tools called: {state.total_tools_called}")
    
    print("PASSED")


def test_safe_tools_auto_approval():
    """Test: Safe tools are auto-approved"""
    print("\n=== Test: Safe Tools Auto-Approval ===")
    
    config = AgenticConfig(
        auto_approve_safe=True,
        verbose=False
    )
    loop = AgenticLoop(config=config)
    
    # Simulate safe tool calls
    tool_calls = [
        {"id": "1", "name": "get_current_directory", "arguments": {}},
        {"id": "2", "name": "list_directory", "arguments": {"path": "."}}
    ]
    
    results, log = loop._execute_tools_with_security(tool_calls)
    
    # All should be approved
    for entry in log:
        assert entry["approved"] == True
        assert entry["dangerous"] == False
    
    print(f"  {len(log)} safe tools auto-approved")
    print("PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Testing Agentic Loop System")
    print("=" * 50)
    
    try:
        test_agentic_config()
        test_loop_state()
        test_agentic_loop_creation()
        test_security_integration()
        test_observation_message_building()
        test_max_iterations_protection()
        test_safe_tools_auto_approval()
        
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
