"""Unit tests for JSON parsing improvements in agent.py."""

import pytest
import json
import sys
import os

# Add agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.agent import Agent


@pytest.fixture
def agent():
    """Create an Agent instance for testing."""
    # Create agent with minimal config
    return Agent(config_path=None)


class TestJSONExtraction:
    """Tests for JSON extraction from LLM responses."""
    
    def test_extract_json_from_markdown_json_block(self, agent):
        """Test extracting JSON from ```json block."""
        response = '''
        Here's the tool call:
        ```json
        {"tool": "fs", "params": {"operation": "read", "path": "test.py"}}
        ```
        That's all.
        '''
        
        json_text = agent._extract_json_from_markdown(response)
        
        assert json_text is not None
        assert '"tool": "fs"' in json_text
    
    def test_extract_json_from_markdown_generic_block(self, agent):
        """Test extracting JSON from generic ``` block."""
        response = '''
        Tool call:
        ```
        {"tool": "terminal", "params": {"command": "ls -la"}}
        ```
        Done.
        '''
        
        json_text = agent._extract_json_from_markdown(response)
        
        assert json_text is not None
        assert '"tool": "terminal"' in json_text
    
    def test_extract_json_from_markdown_no_blocks(self, agent):
        """Test when no markdown blocks present."""
        response = 'Just plain text without any JSON'
        
        json_text = agent._extract_json_from_markdown(response)
        
        assert json_text is None
    
    def test_extract_json_braces_simple(self, agent):
        """Test extracting JSON by finding braces."""
        response = 'I think {"tool": "fs", "params": {}} would work'
        
        json_text = agent._extract_json_braces(response)
        
        assert json_text is not None
        assert json_text.startswith('{')
        assert json_text.endswith('}')
    
    def test_extract_json_braces_nested(self, agent):
        """Test extracting JSON with nested braces."""
        response = '''
        The call should be:
        {"tool": "fs", "params": {"operation": "write", "data": {"key": "value"}}}
        End of message.
        '''
        
        json_text = agent._extract_json_braces(response)
        
        assert json_text is not None
        # Should extract the full JSON
        parsed = json.loads(json_text)
        assert parsed['tool'] == 'fs'
        assert 'data' in parsed['params']
    
    def test_extract_json_braces_no_json(self, agent):
        """Test when no JSON-like structure present."""
        response = 'This is just text without any braces'
        
        json_text = agent._extract_json_braces(response)
        
        assert json_text is None


class TestJSONCleaning:
    """Tests for JSON artifact cleaning."""
    
    def test_clean_trailing_commas(self, agent):
        """Test removing trailing commas."""
        json_text = '{"tool": "fs", "params": {"path": "test.py",},}'
        
        cleaned = agent._clean_json_artifacts(json_text)
        
        # Should remove trailing commas
        assert ',}' not in cleaned
        assert ',"}' not in cleaned
    
    def test_clean_duplicate_commas(self, agent):
        """Test removing duplicate commas."""
        json_text = '{"tool": "fs",, "params": {}}'
        
        cleaned = agent._clean_json_artifacts(json_text)
        
        assert ',,' not in cleaned
    
    def test_clean_stray_characters(self, agent):
        """Test removing stray characters before/after JSON."""
        json_text = 'Sure! {"tool": "fs"} is the call.'
        
        cleaned = agent._clean_json_artifacts(json_text)
        
        assert cleaned.startswith('{')
        assert cleaned.endswith('}')
    
    def test_clean_whitespace_in_keys(self, agent):
        """Test cleaning whitespace in keys."""
        json_text = '{"tool" : "fs" , "params" : {}}'
        
        cleaned = agent._clean_json_artifacts(json_text)
        
        # Should be parseable
        parsed = json.loads(cleaned)
        assert 'tool' in parsed


class TestJSONParsing:
    """Tests for JSON parsing with recovery."""
    
    def test_parse_valid_json(self, agent):
        """Test parsing valid JSON."""
        json_text = '{"tool": "fs", "params": {"operation": "read"}}'
        
        result = agent._parse_json_with_recovery(json_text)
        
        assert result is not None
        assert result['tool'] == 'fs'
    
    def test_parse_single_quotes(self, agent):
        """Test parsing JSON with single quotes."""
        json_text = "{'tool': 'fs', 'params': {'operation': 'read'}}"
        
        result = agent._parse_json_with_recovery(json_text)
        
        assert result is not None
        assert result['tool'] == 'fs'
    
    def test_parse_invalid_json_returns_none(self, agent):
        """Test that invalid JSON returns None after recovery attempts."""
        json_text = 'not json at all'
        
        result = agent._parse_json_with_recovery(json_text)
        
        assert result is None
    
    def test_parse_trailing_comma_recovery(self, agent):
        """Test parsing JSON with trailing comma."""
        json_text = '{"tool": "fs", "params": {},}'
        
        # First clean, then parse
        cleaned = agent._clean_json_artifacts(json_text)
        result = agent._parse_json_with_recovery(cleaned)
        
        assert result is not None


class TestIntegration:
    """Integration tests for full JSON extraction and parsing flow."""
    
    def test_full_extraction_markdown(self, agent):
        """Test full extraction from markdown response."""
        response = '''
        I'll use the filesystem tool:
        ```json
        {"tool": "fs", "params": {"operation": "read", "path": "main.py"}}
        ```
        '''
        
        json_text = agent._extract_json_from_markdown(response)
        assert json_text is not None
        
        cleaned = agent._clean_json_artifacts(json_text)
        result = agent._parse_json_with_recovery(cleaned)
        
        assert result is not None
        assert result['tool'] == 'fs'
        assert result['params']['path'] == 'main.py'
    
    def test_full_extraction_no_markdown(self, agent):
        """Test full extraction without markdown blocks."""
        response = '''
        I think {"tool": "terminal", "params": {"command": "pwd"}} would work here.
        What do you think?
        '''
        
        json_text = agent._extract_json_braces(response)
        assert json_text is not None
        
        cleaned = agent._clean_json_artifacts(json_text)
        result = agent._parse_json_with_recovery(cleaned)
        
        assert result is not None
        assert result['tool'] == 'terminal'
    
    def test_full_extraction_with_artifacts(self, agent):
        """Test extraction with common LLM artifacts."""
        response = '''
        Here's the call:
        ```
        {"tool": "fs", "params": {"operation": "write", "path": "test.py",},}
        ```
        Let me know!
        '''
        
        json_text = agent._extract_json_from_markdown(response)
        assert json_text is not None
        
        cleaned = agent._clean_json_artifacts(json_text)
        result = agent._parse_json_with_recovery(cleaned)
        
        assert result is not None
        assert result['tool'] == 'fs'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
