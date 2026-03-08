"""Tests for new tool integrations: code_tools and subagents."""

import pytest
import asyncio
from pathlib import Path

# Import the components we're testing
from agent.agent import TOOL_PARAMS_SCHEMA, validate_tool_call
from agent.skills_manager import SkillManager, SubAgentsSkill, CodeToolsSkill
from agent.config import Config


class TestToolParamsSchema:
    """Test TOOL_PARAMS_SCHEMA includes new tools."""

    def test_code_tools_in_schema(self):
        """Verify code_tools is in the schema."""
        assert 'code_tools' in TOOL_PARAMS_SCHEMA

    def test_subagents_in_schema(self):
        """Verify subagents is in the schema."""
        assert 'subagents' in TOOL_PARAMS_SCHEMA

    def test_code_tools_required_fields(self):
        """Verify code_tools has correct required fields."""
        schema = TOOL_PARAMS_SCHEMA['code_tools']
        assert 'action' in schema['required']
        assert 'language' in schema['required']

    def test_code_tools_actions(self):
        """Verify code_tools has correct actions."""
        schema = TOOL_PARAMS_SCHEMA['code_tools']
        actions = schema['properties']['action']['enum']
        assert 'lint' in actions
        assert 'format' in actions
        assert 'fix' in actions
        assert 'install' in actions

    def test_code_tools_languages(self):
        """Verify code_tools supports multiple languages."""
        # Language field exists and is a string type
        schema = TOOL_PARAMS_SCHEMA['code_tools']
        assert schema['properties']['language']['type'] == 'string'

    def test_subagents_required_fields(self):
        """Verify subagents has correct required fields."""
        schema = TOOL_PARAMS_SCHEMA['subagents']
        assert 'type' in schema['required']
        assert 'task' in schema['required']

    def test_subagents_types(self):
        """Verify subagents has correct types."""
        schema = TOOL_PARAMS_SCHEMA['subagents']
        types = schema['properties']['type']['enum']
        assert 'code' in types
        assert 'test' in types
        assert 'docs' in types
        assert 'research' in types
        assert 'security' in types

    def test_subagents_context_optional(self):
        """Verify subagents context is optional (not in required)."""
        schema = TOOL_PARAMS_SCHEMA['subagents']
        assert 'context' not in schema['required']
        assert 'context' in schema['properties']


class TestToolCallValidation:
    """Test validate_tool_call function with new tools."""

    def test_valid_code_tools_call(self):
        """Test valid code_tools tool call."""
        tool_call = {
            'tool': 'code_tools',
            'params': {
                'action': 'lint',
                'language': 'python',
                'file_path': 'main.py'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is True
        assert error is None

    def test_code_tools_missing_action(self):
        """Test code_tools call missing action."""
        tool_call = {
            'tool': 'code_tools',
            'params': {
                'language': 'python',
                'file_path': 'main.py'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is False
        assert 'action' in error

    def test_code_tools_missing_language(self):
        """Test code_tools call missing language."""
        tool_call = {
            'tool': 'code_tools',
            'params': {
                'action': 'lint',
                'file_path': 'main.py'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is False
        assert 'language' in error

    def test_code_tools_invalid_action(self):
        """Test code_tools call with invalid action."""
        tool_call = {
            'tool': 'code_tools',
            'params': {
                'action': 'invalid_action',
                'language': 'python',
                'file_path': 'main.py'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is False
        assert 'enum' in error.lower() or 'invalid' in error.lower()

    def test_valid_subagents_call(self):
        """Test valid subagents tool call."""
        tool_call = {
            'tool': 'subagents',
            'params': {
                'type': 'code',
                'task': 'Refactor main.py to use async/await',
                'context': {'file_path': 'main.py'}
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is True
        assert error is None

    def test_subagents_missing_type(self):
        """Test subagents call missing type."""
        tool_call = {
            'tool': 'subagents',
            'params': {
                'task': 'Refactor main.py'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is False
        assert 'type' in error

    def test_subagents_missing_task(self):
        """Test subagents call missing task."""
        tool_call = {
            'tool': 'subagents',
            'params': {
                'type': 'code'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is False
        assert 'task' in error

    def test_subagents_invalid_type(self):
        """Test subagents call with invalid type."""
        tool_call = {
            'tool': 'subagents',
            'params': {
                'type': 'invalid_type',
                'task': 'Do something'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is False
        assert 'enum' in error.lower() or 'invalid' in error.lower()

    def test_subagents_without_context(self):
        """Test subagents call without context (should be valid)."""
        tool_call = {
            'tool': 'subagents',
            'params': {
                'type': 'docs',
                'task': 'Write documentation'
            }
        }
        valid, error = validate_tool_call(tool_call)
        assert valid is True
        assert error is None


class TestSubAgentsSkill:
    """Test SubAgentsSkill class."""

    def test_subagents_skill_initialization(self):
        """Test SubAgentsSkill initializes correctly."""
        config = Config()
        skill = SubAgentsSkill(config)

        assert skill.name == 'subagents'
        assert skill.enabled is True

        # Orchestrator is now lazy-loaded (requires model_manager)
        # So it will be None until model_manager is set
        assert skill.orchestrator is None  # Lazy initialization

    @pytest.mark.asyncio
    async def test_subagents_skill_execute(self):
        """Test SubAgentsSkill execute method."""
        config = Config()
        skill = SubAgentsSkill(config)
        
        # Check if subagents are available
        if skill.orchestrator is None:
            pytest.skip("SubAgents not available")
        
        # Execute a simple task
        result = await skill.execute(
            type='code',
            task='Analyze this simple Python code: def hello(): return "world"',
            context={}
        )
        
        # Should return a result dict
        assert isinstance(result, dict)
        assert 'success' in result
        
        # Note: The actual execution may fail due to LLM API requirements,
        # but the skill should handle it gracefully
        if result['success']:
            assert 'output' in result
            assert 'stats' in result
        else:
            # If it fails, should have an error message
            assert 'error' in result


class TestCodeToolsSkill:
    """Test CodeToolsSkill class."""

    def test_code_tools_skill_initialization(self):
        """Test CodeToolsSkill initializes correctly."""
        config = Config()
        
        try:
            from agent.code_analysis_tools import CodeTools
            # If we can import, code tools are available
        except ImportError:
            pytest.skip("CodeTools module not found")
        
        skill = CodeToolsSkill(config)
        
        assert skill.name == 'code_tools'
        assert skill.enabled is True
        assert hasattr(skill, 'tools')

    @pytest.mark.asyncio
    async def test_code_tools_lint_action(self):
        """Test CodeToolsSkill lint action."""
        config = Config()
        
        try:
            from agent.code_analysis_tools import CodeTools
        except ImportError:
            pytest.skip("CodeTools module not found")
        
        skill = CodeToolsSkill(config)
        
        # Test linting valid Python code
        result = await skill.execute(
            action='lint',
            language='python',
            content='def hello():\n    return "world"'
        )
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert result['action'] == 'lint'

    @pytest.mark.asyncio
    async def test_code_tools_format_action(self):
        """Test CodeToolsSkill format action."""
        config = Config()
        
        try:
            from agent.code_analysis_tools import CodeTools
        except ImportError:
            pytest.skip("CodeTools module not found")
        
        skill = CodeToolsSkill(config)
        
        # Test formatting valid Python code
        result = await skill.execute(
            action='format',
            language='python',
            content='def hello( ):return "world"'
        )
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert result['action'] == 'format'


class TestSkillManagerIntegration:
    """Test SkillManager includes new skills."""

    def test_skill_manager_has_code_tools(self):
        """Test SkillManager initializes with code_tools."""
        config = Config()
        manager = SkillManager(config)
        
        try:
            from agent.code_analysis_tools import CODE_TOOLS_AVAILABLE
            if CODE_TOOLS_AVAILABLE:
                assert 'code_tools' in manager.skills
            else:
                # Skill may not be registered if tools unavailable
                pass
        except ImportError:
            pass

    def test_skill_manager_has_subagents(self):
        """Test SkillManager initializes with subagents."""
        config = Config()
        manager = SkillManager(config)
        
        try:
            from agent.subagents import SUBAGENTS_AVAILABLE
            if SUBAGENTS_AVAILABLE:
                assert 'subagents' in manager.skills
            else:
                # Skill may not be registered if subagents unavailable
                pass
        except ImportError:
            pass

    @pytest.mark.asyncio
    async def test_skill_manager_execute_code_tools(self):
        """Test SkillManager can execute code_tools."""
        config = Config()
        manager = SkillManager(config)

        try:
            from agent.code_analysis_tools import CodeTools
        except ImportError:
            pytest.skip("CodeTools module not found")

        if 'code_tools' not in manager.registry.tools:
            pytest.skip("code_tools skill not registered")

        result = await manager.execute(
            'code_tools',
            action='lint',
            language='python',
            content='x = 1'
        )

        assert isinstance(result, dict)
        assert 'success' in result

    @pytest.mark.asyncio
    async def test_skill_manager_execute_subagents(self):
        """Test SkillManager can execute subagents."""
        config = Config()
        manager = SkillManager(config)

        try:
            from agent.subagents.orchestrator import SubAgentOrchestrator
        except ImportError:
            pytest.skip("SubAgents module not found")

        if 'subagents' not in manager.registry.tools:
            pytest.skip("subagents skill not registered")

        result = await manager.execute(
            'subagents',
            type='code',
            task='Simple task',
            context={}
        )

        assert isinstance(result, dict)
        assert 'success' in result


class TestSystemPrompt:
    """Test system prompt includes correct tools."""

    def test_system_prompt_no_lsp(self):
        """Test system prompt does NOT mention dead lsp tool."""
        from agent.agent import Agent
        from agent.config import Config
        
        config = Config()
        agent = Agent(config_path=None)
        
        import inspect
        source = inspect.getsource(agent._build_standard_context)
        
        # lsp should NOT be in the system prompt
        assert '"lsp"' not in source
        assert 'lsp' not in source.lower() or 'LSPContextOptimizer' in source  # Allow only in class names

    def test_system_prompt_mentions_code_tools(self):
        """Test system prompt documents code_tools."""
        from agent.agent import Agent
        from agent.config import Config
        
        config = Config()
        agent = Agent(config_path=None)
        
        import inspect
        source = inspect.getsource(agent._build_standard_context)
        
        assert 'code_tools' in source
        assert 'lint' in source
        assert 'format' in source

    def test_system_prompt_mentions_subagents(self):
        """Test system prompt documents subagents."""
        from agent.agent import Agent
        from agent.config import Config
        
        config = Config()
        agent = Agent(config_path=None)
        
        import inspect
        source = inspect.getsource(agent._build_standard_context)
        
        assert 'subagents' in source
        assert 'code' in source
        assert 'test' in source
        assert 'docs' in source

    def test_system_prompt_special_commands(self):
        """Test system prompt documents special commands."""
        from agent.agent import Agent
        from agent.config import Config
        
        config = Config()
        agent = Agent(config_path=None)
        
        import inspect
        source = inspect.getsource(agent._build_standard_context)
        
        assert 'subagents list' in source
        assert 'subagents status' in source
        assert '/stats' in source
        assert '/model' in source

    def test_system_prompt_has_correct_tool_count(self):
        """Test system prompt has 6 tools (not 7 with lsp)."""
        from agent.agent import Agent
        from agent.config import Config
        
        config = Config()
        agent = Agent(config_path=None)
        
        import inspect
        source = inspect.getsource(agent._build_standard_context)
        
        # Count tool numbers in prompt
        assert '1. "fs"' in source
        assert '2. "terminal"' in source
        assert '3. "web"' in source
        assert '4. "search"' in source
        assert '5. "code_tools"' in source
        assert '6. "subagents"' in source
        # Should NOT have tool 7
        assert '7.' not in source
