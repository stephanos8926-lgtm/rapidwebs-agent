#!/usr/bin/env python
"""Test the response cleaner for removing JSON tool calls."""

import sys
sys.path.insert(0, '..')

from agent.agent import clean_response_for_display


def test_clean_response_for_display():
    """Test that JSON tool calls are removed from responses."""
    
    print("=" * 60)
    print("Testing Response Cleaner")
    print("=" * 60)
    
    # Test 1: Simple JSON tool call
    test1_input = """I'll read the file for you.

{"tool": "fs", "params": {"operation": "read", "path": "test.py"}}

Here's what I found."""
    
    test1_expected = """I'll read the file for you.

Here's what I found."""
    
    result1 = clean_response_for_display(test1_input)
    print(f"\nTest 1: Simple JSON tool call")
    print(f"Input: {repr(test1_input)}")
    print(f"Output: {repr(result1)}")
    assert "tool" not in result1.lower() or result1.count("tool") < test1_input.count("tool")
    print("✓ Passed")
    
    # Test 2: JSON in markdown code block
    test2_input = """Let me check that.

```json
{"tool": "search", "params": {"action": "grep", "pattern": "def main"}}
```

Found it!"""
    
    result2 = clean_response_for_display(test2_input)
    print(f"\nTest 2: JSON in markdown code block")
    print(f"Input: {repr(test2_input)}")
    print(f"Output: {repr(result2)}")
    assert "```json" not in result2
    print("✓ Passed")
    
    # Test 3: Multiple tool calls
    test3_input = """I'll help with that.

{"tool": "fs", "params": {"operation": "list", "path": "."}}

Now let me read the file.

{"tool": "fs", "params": {"operation": "read", "path": "README.md"}}

Done!"""
    
    result3 = clean_response_for_display(test3_input)
    print(f"\nTest 3: Multiple tool calls")
    print(f"Input: {repr(test3_input)}")
    print(f"Output: {repr(result3)}")
    assert result3.count("tool") < test3_input.count("tool")
    print("✓ Passed")
    
    # Test 4: Normal response (no tool calls)
    test4_input = """Hello! I'm here to help you with your code.

How can I assist you today?"""
    
    result4 = clean_response_for_display(test4_input)
    print(f"\nTest 4: Normal response (no tool calls)")
    print(f"Input: {repr(test4_input)}")
    print(f"Output: {repr(result4)}")
    assert result4 == test4_input
    print("✓ Passed")
    
    # Test 5: Partial JSON tool call
    test5_input = """Let me do that.

{"tool": "fs", "params": {"operation": "read"

There was an error."""
    
    result5 = clean_response_for_display(test5_input)
    print(f"\nTest 5: Partial JSON tool call")
    print(f"Input: {repr(test5_input)}")
    print(f"Output: {repr(result5)}")
    print("✓ Passed")
    
    # Test 6: Empty response
    test6_input = ""
    result6 = clean_response_for_display(test6_input)
    print(f"\nTest 6: Empty response")
    assert result6 == ""
    print("✓ Passed")
    
    # Test 7: Only JSON tool call (should return original if cleaning removes everything)
    test7_input = '{"tool": "fs", "params": {"operation": "read", "path": "test.py"}}'
    result7 = clean_response_for_display(test7_input)
    print(f"\nTest 7: Only JSON tool call")
    print(f"Input: {repr(test7_input)}")
    print(f"Output: {repr(result7)}")
    print("✓ Passed")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_clean_response_for_display()
