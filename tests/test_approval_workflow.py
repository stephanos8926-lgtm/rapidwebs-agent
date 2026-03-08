#!/usr/bin/env python
"""Test script for Approval Workflow implementation.

This script tests all aspects of the approval workflow system:
- ApprovalMode enum
- RiskLevel enum
- ApprovalManager functionality
- Tool risk classification
- Mode switching
- Auto-accept/reject functionality
"""

import sys
from pathlib import Path

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.approval_workflow import ApprovalMode, RiskLevel, ApprovalManager, ToolApproval
from agent.config import Config


def test_enums():
    """Test ApprovalMode and RiskLevel enums."""
    print("=" * 60)
    print("Testing Enums")
    print("=" * 60)
    
    # Test ApprovalMode
    assert ApprovalMode.PLAN.value == "plan"
    assert ApprovalMode.DEFAULT.value == "default"
    assert ApprovalMode.AUTO_EDIT.value == "auto_edit"
    assert ApprovalMode.YOLO.value == "yolo"
    print("✓ ApprovalMode enum values correct")
    
    # Test RiskLevel
    assert RiskLevel.READ.value == "read"
    assert RiskLevel.WRITE.value == "write"
    assert RiskLevel.DESTRUCTIVE.value == "danger"
    print("✓ RiskLevel enum values correct")
    
    print()


def test_approval_manager_init():
    """Test ApprovalManager initialization."""
    print("=" * 60)
    print("Testing ApprovalManager Initialization")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    
    assert mgr.mode == ApprovalMode.DEFAULT
    assert len(mgr.auto_accept_tools) == 0
    assert len(mgr.auto_reject_tools) == 0
    print("✓ ApprovalManager initialized with DEFAULT mode")
    print(f"  Initial mode: {mgr.get_mode().value}")
    print(f"  Auto-accept count: {mgr.get_auto_accept_count()}")
    print(f"  Auto-reject count: {mgr.get_auto_reject_count()}")
    print()


def test_tool_risk_classification():
    """Test tool risk level classification."""
    print("=" * 60)
    print("Testing Tool Risk Classification")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    
    # Test filesystem operations
    assert mgr.get_tool_risk('fs', {'operation': 'read'}) == RiskLevel.READ
    assert mgr.get_tool_risk('fs', {'operation': 'list'}) == RiskLevel.READ
    assert mgr.get_tool_risk('fs', {'operation': 'explore'}) == RiskLevel.READ
    print("✓ FS read/list/explore classified as READ")
    
    assert mgr.get_tool_risk('fs', {'operation': 'write'}) == RiskLevel.WRITE
    print("✓ FS write classified as WRITE")
    
    assert mgr.get_tool_risk('fs', {'operation': 'delete'}) == RiskLevel.DESTRUCTIVE
    print("✓ FS delete classified as DESTRUCTIVE")
    
    # Test terminal
    assert mgr.get_tool_risk('terminal', {'command': 'ls'}) == RiskLevel.DESTRUCTIVE
    print("✓ Terminal classified as DESTRUCTIVE")
    
    # Test web
    assert mgr.get_tool_risk('web', {'url': 'https://example.com'}) == RiskLevel.READ
    print("✓ Web classified as READ")
    
    # Test LSP
    assert mgr.get_tool_risk('lsp', {'action': 'check'}) == RiskLevel.READ
    assert mgr.get_tool_risk('lsp', {'action': 'format'}) == RiskLevel.WRITE
    assert mgr.get_tool_risk('lsp', {'action': 'fix'}) == RiskLevel.WRITE
    print("✓ LSP check classified as READ, format/fix as WRITE")
    
    # Test search
    assert mgr.get_tool_risk('search', {'action': 'grep'}) == RiskLevel.READ
    print("✓ Search classified as READ")
    
    # Test code_tools
    assert mgr.get_tool_risk('code_tools', {'action': 'lint'}) == RiskLevel.READ
    assert mgr.get_tool_risk('code_tools', {'action': 'format'}) == RiskLevel.WRITE
    print("✓ Code tools lint classified as READ, format as WRITE")
    
    print()


def test_requires_approval_default_mode():
    """Test approval requirements in DEFAULT mode."""
    print("=" * 60)
    print("Testing Approval Requirements (DEFAULT mode)")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    mgr.set_mode('default')
    
    # Read operations should NOT require approval
    assert not mgr.requires_approval('fs', {'operation': 'read'})
    assert not mgr.requires_approval('fs', {'operation': 'list'})
    assert not mgr.requires_approval('web', {'url': 'https://example.com'})
    assert not mgr.requires_approval('search', {'action': 'grep'})
    print("✓ Read operations do NOT require approval")
    
    # Write operations SHOULD require approval
    assert mgr.requires_approval('fs', {'operation': 'write'})
    assert mgr.requires_approval('lsp', {'action': 'format'})
    print("✓ Write operations require approval")
    
    # Destructive operations SHOULD require approval
    assert mgr.requires_approval('fs', {'operation': 'delete'})
    assert mgr.requires_approval('terminal', {'command': 'rm -rf'})
    print("✓ Destructive operations require approval")
    
    print()


def test_requires_approval_plan_mode():
    """Test approval requirements in PLAN mode."""
    print("=" * 60)
    print("Testing Approval Requirements (PLAN mode)")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    mgr.set_mode('plan')
    
    # Read operations should NOT require approval (allowed in plan mode)
    assert not mgr.requires_approval('fs', {'operation': 'read'})
    assert not mgr.requires_approval('search', {'action': 'grep'})
    print("✓ Read operations allowed in PLAN mode")
    
    # Write/destructive operations SHOULD require approval (blocked)
    assert mgr.requires_approval('fs', {'operation': 'write'})
    assert mgr.requires_approval('fs', {'operation': 'delete'})
    assert mgr.requires_approval('terminal', {'command': 'ls'})
    print("✓ Write/destructive operations blocked in PLAN mode")
    
    print()


def test_requires_approval_auto_edit_mode():
    """Test approval requirements in AUTO_EDIT mode."""
    print("=" * 60)
    print("Testing Approval Requirements (AUTO_EDIT mode)")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    mgr.set_mode('auto_edit')
    
    # Read operations should NOT require approval
    assert not mgr.requires_approval('fs', {'operation': 'read'})
    print("✓ Read operations do NOT require approval")
    
    # Write operations should NOT require approval (auto-edit mode)
    assert not mgr.requires_approval('fs', {'operation': 'write'})
    assert not mgr.requires_approval('lsp', {'action': 'format'})
    print("✓ Write operations do NOT require approval (auto-accepted)")
    
    # Destructive operations SHOULD require approval
    assert mgr.requires_approval('fs', {'operation': 'delete'})
    assert mgr.requires_approval('terminal', {'command': 'rm'})
    print("✓ Destructive operations require approval")
    
    print()


def test_requires_approval_yolo_mode():
    """Test approval requirements in YOLO mode."""
    print("=" * 60)
    print("Testing Approval Requirements (YOLO mode)")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    mgr.set_mode('yolo')
    
    # Nothing should require approval in YOLO mode
    assert not mgr.requires_approval('fs', {'operation': 'read'})
    assert not mgr.requires_approval('fs', {'operation': 'write'})
    assert not mgr.requires_approval('fs', {'operation': 'delete'})
    assert not mgr.requires_approval('terminal', {'command': 'rm -rf'})
    print("✓ NO operations require approval in YOLO mode")
    
    print()


def test_auto_accept_reject():
    """Test auto-accept and auto-reject functionality."""
    print("=" * 60)
    print("Testing Auto-Accept/Reject Functionality")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    mgr.set_mode('default')
    
    # Initially should require approval
    assert mgr.requires_approval('fs', {'operation': 'write'})
    print("✓ FS write initially requires approval")
    
    # Mark as auto-accept
    mgr.mark_auto_accept('fs', {'operation': 'write'})
    assert not mgr.requires_approval('fs', {'operation': 'write'})
    print("✓ After auto-accept, FS write does NOT require approval")
    
    # Test auto-reject
    mgr.mark_auto_reject('terminal', {'command': 'rm'})
    assert mgr.requires_approval('terminal', {'command': 'rm'})
    print("✓ After auto-reject, terminal still requires approval (blocked)")
    
    print(f"  Auto-accept count: {mgr.get_auto_accept_count()}")
    print(f"  Auto-reject count: {mgr.get_auto_reject_count()}")
    
    print()


def test_mode_switching():
    """Test mode switching functionality."""
    print("=" * 60)
    print("Testing Mode Switching")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    
    # Test valid mode switches
    assert mgr.set_mode('plan')
    assert mgr.get_mode() == ApprovalMode.PLAN
    print("✓ Switched to PLAN mode")
    
    assert mgr.set_mode('default')
    assert mgr.get_mode() == ApprovalMode.DEFAULT
    print("✓ Switched to DEFAULT mode")
    
    assert mgr.set_mode('auto-edit')
    assert mgr.get_mode() == ApprovalMode.AUTO_EDIT
    print("✓ Switched to AUTO_EDIT mode")
    
    assert mgr.set_mode('yolo')
    assert mgr.get_mode() == ApprovalMode.YOLO
    print("✓ Switched to YOLO mode")
    
    # Test invalid mode
    assert not mgr.set_mode('invalid_mode')
    print("✓ Invalid mode rejected")
    
    print()


def test_mode_descriptions():
    """Test mode description functionality."""
    print("=" * 60)
    print("Testing Mode Descriptions")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    
    for mode in ApprovalMode:
        mgr.set_mode(mode.value)
        desc = mgr.get_mode_description()
        assert len(desc) > 0
        print(f"  {mode.value.upper()}: {desc}")
    
    print()


def test_session_state_clear():
    """Test session state clearing."""
    print("=" * 60)
    print("Testing Session State Clear")
    print("=" * 60)
    
    config = Config()
    mgr = ApprovalManager(config)
    
    # Add some auto-accept/reject entries
    mgr.mark_auto_accept('fs', {'operation': 'write'})
    mgr.mark_auto_reject('terminal', {'command': 'rm'})
    
    assert mgr.get_auto_accept_count() == 1
    assert mgr.get_auto_reject_count() == 1
    print("✓ Added auto-accept/reject entries")
    
    # Clear session state
    mgr.clear_session_state()
    
    assert mgr.get_auto_accept_count() == 0
    assert mgr.get_auto_reject_count() == 0
    print("✓ Session state cleared")
    
    print()


def run_all_tests():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "APPROVAL WORKFLOW TEST SUITE" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    try:
        test_enums()
        test_approval_manager_init()
        test_tool_risk_classification()
        test_requires_approval_default_mode()
        test_requires_approval_plan_mode()
        test_requires_approval_auto_edit_mode()
        test_requires_approval_yolo_mode()
        test_auto_accept_reject()
        test_mode_switching()
        test_mode_descriptions()
        test_session_state_clear()
        
        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print("\n")
        print("Summary:")
        print("  - ApprovalMode enum: ✓")
        print("  - RiskLevel enum: ✓")
        print("  - ApprovalManager initialization: ✓")
        print("  - Tool risk classification: ✓")
        print("  - DEFAULT mode approval: ✓")
        print("  - PLAN mode approval: ✓")
        print("  - AUTO_EDIT mode approval: ✓")
        print("  - YOLO mode approval: ✓")
        print("  - Auto-accept/reject: ✓")
        print("  - Mode switching: ✓")
        print("  - Mode descriptions: ✓")
        print("  - Session state clear: ✓")
        print("\n")
        return True
        
    except AssertionError as e:
        print("=" * 60)
        print("TEST FAILED! ✗")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print("=" * 60)
        print("TEST ERROR! ✗")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
