#!/usr/bin/env python
"""Test script to verify SubAgent error handling fixes.

This script tests that SubAgents properly return errors instead of 
placeholder content when the LLM is not configured.
"""

import asyncio
import sys
from pathlib import Path

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.subagents.code_agent import CodeAgent
from agent.subagents.docs_agent import DocsAgent
from agent.subagents.test_agent import TestAgent
from agent.subagents.protocol import SubAgentTask, SubAgentType, SubAgentStatus


async def test_code_agent_error_handling():
    """Test CodeAgent returns proper errors when LLM not configured."""
    print("\n" + "="*60)
    print("Testing CodeAgent Error Handling")
    print("="*60)
    
    agent = CodeAgent(model_manager=None)
    
    # Create a test task for refactoring
    task = SubAgentTask.create(
        SubAgentType.CODE,
        "Refactor this file to use async/await",
        context={
            'type': 'refactor',
            'file_path': 'test_subagent_fixes.py',
            'instructions': 'Make it async'
        }
    )
    
    try:
        result = await agent.execute(task)
        
        print(f"\nTask Status: {result.status}")
        print(f"Task Output: {result.output[:200] if result.output else 'N/A'}")
        print(f"Task Error: {result.error[:200] if result.error else 'N/A'}")
        print(f"Token Usage: {result.token_usage}")
        
        # Verify error is properly returned
        if result.status == SubAgentStatus.FAILED and result.error:
            if "LLM not configured" in result.error or "not configured" in result.error:
                print("\n✅ PASS: Proper error returned for unconfigured LLM")
                return True
            else:
                print(f"\n⚠️ PARTIAL: Got error but message could be clearer: {result.error}")
                return True
        elif result.status == SubAgentStatus.COMPLETED:
            print("\n❌ FAIL: Task completed when it should have failed (LLM not configured)")
            return False
        else:
            print(f"\n❌ FAIL: Unexpected result status: {result.status}")
            return False
            
    except Exception as e:
        print(f"\n❌ FAIL: Exception raised: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_docs_agent_error_handling():
    """Test DocsAgent returns proper errors when LLM not configured."""
    print("\n" + "="*60)
    print("Testing DocsAgent Error Handling")
    print("="*60)
    
    agent = DocsAgent(model_manager=None)
    
    # Create a test task for API docs
    task = SubAgentTask.create(
        SubAgentType.DOCS,
        "Generate API documentation for this file",
        context={
            'type': 'api',
            'source_file': 'test_subagent_fixes.py',
            'format': 'markdown'
        }
    )
    
    try:
        result = await agent.execute(task)
        
        print(f"\nTask Status: {result.status}")
        print(f"Task Output: {result.output[:200] if result.output else 'N/A'}")
        print(f"Task Error: {result.error[:200] if result.error else 'N/A'}")
        print(f"Token Usage: {result.token_usage}")
        
        # Verify error is properly returned
        if result.status == SubAgentStatus.FAILED and result.error:
            if "LLM not configured" in result.error or "ERROR:" in result.error:
                print("\n✅ PASS: Proper error returned for unconfigured LLM")
                return True
            else:
                print(f"\n⚠️ PARTIAL: Got error but message could be clearer: {result.error}")
                return True
        elif result.status == SubAgentStatus.COMPLETED:
            print("\n❌ FAIL: Task completed when it should have failed (LLM not configured)")
            return False
        else:
            print(f"\n❌ FAIL: Unexpected result status: {result.status}")
            return False
            
    except Exception as e:
        print(f"\n❌ FAIL: Exception raised: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_test_agent_error_handling():
    """Test TestAgent returns proper errors when LLM not configured."""
    print("\n" + "="*60)
    print("Testing TestAgent Error Handling")
    print("="*60)
    
    agent = TestAgent(model_manager=None)
    
    # Create a test task for test generation
    task = SubAgentTask.create(
        SubAgentType.TEST,
        "Write tests for this file",
        context={
            'type': 'generate',
            'source_file': 'test_subagent_fixes.py',
            'framework': 'pytest'
        }
    )
    
    try:
        result = await agent.execute(task)
        
        print(f"\nTask Status: {result.status}")
        print(f"Task Output: {result.output[:200] if result.output else 'N/A'}")
        print(f"Task Error: {result.error[:200] if result.error else 'N/A'}")
        print(f"Token Usage: {result.token_usage}")
        
        # Verify error is properly returned
        if result.status == SubAgentStatus.FAILED and result.error:
            if "LLM not configured" in result.error:
                print("\n✅ PASS: Proper error returned for unconfigured LLM")
                return True
            else:
                print(f"\n⚠️ PARTIAL: Got error but message could be clearer: {result.error}")
                return True
        elif result.status == SubAgentStatus.COMPLETED:
            print("\n❌ FAIL: Task completed when it should have failed (LLM not configured)")
            return False
        else:
            print(f"\n❌ FAIL: Unexpected result status: {result.status}")
            return False
            
    except Exception as e:
        print(f"\n❌ FAIL: Exception raised: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SubAgent Error Handling Test Suite")
    print("="*60)
    print("\nThese tests verify that SubAgents return proper errors")
    print("instead of placeholder content when LLM is not configured.\n")
    
    results = []
    
    # Run tests
    results.append(("CodeAgent", await test_code_agent_error_handling()))
    results.append(("DocsAgent", await test_docs_agent_error_handling()))
    results.append(("TestAgent", await test_test_agent_error_handling()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! SubAgent error handling is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
