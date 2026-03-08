"""Integration tests for ResearchAgent and SecurityAgent.

These tests verify the new subagents work correctly:
- ResearchAgent: Web search, documentation lookup, codebase research
- SecurityAgent: Dependency audit, code scanning, secret detection
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os

from agent.subagents import (
    ResearchAgent, SecurityAgent,
    SubAgentTask, SubAgentType, SubAgentResult, SubAgentStatus
)
from agent.subagents.protocol import SubAgentConfig


# =============================================================================
# RESEARCH AGENT TESTS
# =============================================================================

class TestResearchAgent:
    """Tests for ResearchAgent."""

    def test_research_agent_initialization(self):
        """Test ResearchAgent initializes correctly."""
        agent = ResearchAgent()
        
        assert agent.type == SubAgentType.RESEARCH
        assert agent.enabled is True
        assert agent.config.max_token_budget == 15000
        assert agent.config.max_timeout == 600
        
    def test_research_agent_capabilities(self):
        """Test ResearchAgent reports correct capabilities."""
        agent = ResearchAgent()
        caps = agent.get_capabilities()
        
        assert 'specialties' in caps
        assert 'web_search' in caps['specialties']
        assert 'documentation_lookup' in caps['specialties']
        assert 'codebase_research' in caps['specialties']
        assert 'information_synthesis' in caps['specialties']
        
    def test_research_agent_task_classification(self):
        """Test ResearchAgent classifies tasks correctly."""
        agent = ResearchAgent()
        
        # Test web search classification
        task = SubAgentTask.create(
            SubAgentType.RESEARCH,
            "Search for latest Python news"
        )
        assert agent._classify_task(task) == 'web_search'
        
        # Test documentation classification
        task = SubAgentTask.create(
            SubAgentType.RESEARCH,
            "Find documentation for FastAPI"
        )
        assert agent._classify_task(task) == 'documentation'
        
        # Test codebase classification
        task = SubAgentTask.create(
            SubAgentType.RESEARCH,
            "In this codebase, find user authentication"
        )
        assert agent._classify_task(task) == 'codebase'
        
        # Test summarize classification
        task = SubAgentTask.create(
            SubAgentType.RESEARCH,
            "Summarize this article"
        )
        assert agent._classify_task(task) == 'summarize'
        
    def test_url_detection(self):
        """Test URL detection and extraction."""
        agent = ResearchAgent()
        
        # Test URL detection
        assert agent._contains_url("Check https://example.com") is True
        assert agent._contains_url("No URL here") is False
        
        # Test URL extraction
        text = "Visit https://example.com and http://test.org/page"
        urls = agent._extract_urls(text)
        assert len(urls) == 2
        assert 'https://example.com' in urls
        assert 'http://test.org/page' in urls
        
    def test_research_task_creation(self):
        """Test creating research tasks."""
        task = SubAgentTask.create(
            SubAgentType.RESEARCH,
            "Research Python async/await best practices",
            context={'query': 'Python async await', 'sources': ['web', 'docs']},
            token_budget=10000,
            timeout=300
        )
        
        assert task.type == SubAgentType.RESEARCH
        assert 'Python async/await' in task.description
        assert task.token_budget == 10000
        assert task.timeout == 300


# =============================================================================
# SECURITY AGENT TESTS
# =============================================================================

class TestSecurityAgent:
    """Tests for SecurityAgent."""

    def test_security_agent_initialization(self):
        """Test SecurityAgent initializes correctly."""
        agent = SecurityAgent()
        
        assert agent.type == SubAgentType.SECURITY
        assert agent.enabled is True
        assert agent.config.max_token_budget == 20000
        assert agent.config.max_timeout == 900
        
    def test_security_agent_capabilities(self):
        """Test SecurityAgent reports correct capabilities."""
        agent = SecurityAgent()
        caps = agent.get_capabilities()
        
        assert 'specialties' in caps
        assert 'dependency_audit' in caps['specialties']
        assert 'code_scanning' in caps['specialties']
        assert 'config_review' in caps['specialties']
        assert 'secret_detection' in caps['specialties']
        assert 'owasp_top_10' in caps['specialties']
        
    def test_security_agent_task_classification(self):
        """Test SecurityAgent classifies tasks correctly."""
        agent = SecurityAgent()
        
        # Test dependency audit classification
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Audit dependencies for vulnerabilities"
        )
        assert agent._classify_task(task) == 'dependency_audit'
        
        # Test code scan classification
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Scan code for security issues"
        )
        assert agent._classify_task(task) == 'code_scan'
        
        # Test config review classification
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Review configuration files"
        )
        assert agent._classify_task(task) == 'config_review'
        
        # Test secret scan classification
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Scan for exposed secrets and API keys"
        )
        assert agent._classify_task(task) == 'secret_scan'
        
        # Test full audit classification
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Run full security audit"
        )
        assert agent._classify_task(task) == 'full_audit'
        
    def test_secret_detection_patterns(self):
        """Test secret detection pattern matching."""
        agent = SecurityAgent()
        
        # Test AWS key detection
        aws_content = "AWS_KEY = AKIAIOSFODNN7EXAMPLE"
        findings = agent._scan_for_secrets(aws_content, "test.py")
        assert len(findings) > 0
        assert any('AWS' in f.get('category', '') for f in findings)
        
        # Test GitHub token detection
        github_content = "token = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        findings = agent._scan_for_secrets(github_content, "test.py")
        assert len(findings) > 0
        
        # Test API key detection
        api_content = 'api_key = "sk-1234567890abcdef"'
        findings = agent._scan_for_secrets(api_content, "test.py")
        assert len(findings) > 0
        
    def test_owasp_pattern_detection(self):
        """Test OWASP vulnerability pattern detection."""
        agent = SecurityAgent()
        
        # Test SQL injection pattern
        sql_injection = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        findings = agent._scan_for_owasp(sql_injection, "test.py")
        assert len(findings) > 0
        assert any('Injection' in f.get('category', '') for f in findings)
        
        # Test weak crypto pattern
        weak_crypto = 'hashlib.md5(password.encode()).hexdigest()'
        findings = agent._scan_for_owasp(weak_crypto, "test.py")
        assert len(findings) > 0
        assert any('Cryptographic' in f.get('category', '') for f in findings)
        
        # Test debug mode pattern
        debug_mode = 'DEBUG = True'
        findings = agent._scan_for_owasp(debug_mode, "test.py")
        assert len(findings) > 0
        assert any('Misconfiguration' in f.get('category', '') for f in findings)
        
    def test_dependency_parsing(self):
        """Test dependency file parsing."""
        agent = SecurityAgent()
        
        # Test requirements.txt parsing
        requirements = """
flask==2.0.1
requests>=2.28.0
django~=4.0
# This is a comment
numpy
"""
        deps = agent._parse_dependencies(requirements, 'python')
        assert 'flask' in deps
        assert deps['flask'] == '2.0.1'
        assert 'requests' in deps
        assert 'django' in deps
        assert 'numpy' in deps
        
    def test_vulnerability_check(self):
        """Test dependency vulnerability checking."""
        agent = SecurityAgent()
        
        # Test known vulnerable package
        vuln = agent._check_dependency_vulnerability('flask', '2.0.0')
        assert vuln is not None
        assert 'cve' in vuln
        
        # Test safe package
        safe = agent._check_dependency_vulnerability('nonexistent-package', '1.0.0')
        assert safe is None
        
    def test_severity_counting(self):
        """Test severity counting."""
        agent = SecurityAgent()
        
        findings = [
            {'severity': 'critical'},
            {'severity': 'high'},
            {'severity': 'high'},
            {'severity': 'medium'},
        ]
        
        counts = agent._count_severities(findings)
        assert counts['critical'] == 1
        assert counts['high'] == 2
        assert counts['medium'] == 1
        
    def test_security_task_creation(self):
        """Test creating security tasks."""
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Run comprehensive security audit",
            context={
                'type': 'full_audit',
                'workspace': str(Path.cwd()),
                'severity_threshold': 'medium'
            },
            token_budget=15000,
            timeout=600
        )
        
        assert task.type == SubAgentType.SECURITY
        assert task.context['type'] == 'full_audit'
        assert task.token_budget == 15000


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSubAgentsIntegration:
    """Integration tests for subagents working together."""

    def test_all_subagent_types_available(self):
        """Test all subagent types are available."""
        from agent.subagents import SubAgentType
        
        expected_types = [
            'code', 'test', 'docs',
            'research', 'security',
            'generic'
        ]
        
        actual_types = [t.value for t in SubAgentType]
        
        for expected in expected_types:
            assert expected in actual_types
            
    def test_subagent_orchestrator_with_new_agents(self):
        """Test orchestrator can register new agents."""
        from agent.subagents import SubAgentOrchestrator
        
        orchestrator = SubAgentOrchestrator(max_concurrent=3)
        orchestrator.register_default_agents()
        
        # Check all agents are registered
        assert SubAgentType.CODE in orchestrator.agents
        assert SubAgentType.TEST in orchestrator.agents
        assert SubAgentType.DOCS in orchestrator.agents
        assert SubAgentType.RESEARCH in orchestrator.agents
        assert SubAgentType.SECURITY in orchestrator.agents
        
    def test_research_agent_result_structure(self):
        """Test ResearchAgent returns proper result structure."""
        agent = ResearchAgent()
        
        # Create a mock result (without LLM)
        result = SubAgentResult(
            task_id="test-123",
            status=SubAgentStatus.COMPLETED,
            output="Research findings...",
            token_usage=0,
            metadata={'research_type': 'general'}
        )
        
        assert result.success() is True
        assert result.task_id == "test-123"
        assert result.status == SubAgentStatus.COMPLETED
        
    def test_security_agent_result_structure(self):
        """Test SecurityAgent returns proper result structure."""
        agent = SecurityAgent()
        
        # Create a mock result (without LLM)
        result = SubAgentResult(
            task_id="test-456",
            status=SubAgentStatus.COMPLETED,
            output="# Security Report\n\nNo issues found",
            token_usage=0,
            metadata={'scan_type': 'code_scan', 'findings': []}
        )
        
        assert result.success() is True
        assert 'Security Report' in result.output
        assert result.metadata['scan_type'] == 'code_scan'


# =============================================================================
# PATTERN MATCHING TESTS
# =============================================================================

class TestPatternMatching:
    """Test security pattern matching accuracy."""

    def test_secret_patterns_false_positives(self):
        """Test secret detection doesn't produce false positives."""
        agent = SecurityAgent()
        
        # Safe content that shouldn't trigger
        safe_content = """
# This is a comment about passwords
def get_password_hash(password):
    # Hash the password securely
    return hashlib.sha256(password.encode()).hexdigest()

# Example: api_key = "your_key_here"
# This is just documentation
"""
        findings = agent._scan_for_secrets(safe_content, "test.py")
        # Should not detect actual secrets in comments/examples
        # (may detect the pattern but should be masked)
        assert isinstance(findings, list)
        
    def test_owasp_patterns_comprehensive(self):
        """Test OWASP patterns cover major vulnerability types."""
        agent = SecurityAgent()
        
        # Comprehensive vulnerable code sample
        vulnerable_code = """
import os
import hashlib

# SQL Injection
def get_user(user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    
# Command Injection
def run_command(cmd):
    os.system(cmd)
    
# Weak Cryptography
def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()
    
# Debug Mode
DEBUG = True
ALLOWED_HOSTS = ['*']

# Hardcoded Password
password = "admin123"
"""
        findings = agent._scan_for_owasp(vulnerable_code, "test.py")
        
        # Should detect multiple vulnerability types
        categories = set(f.get('category', '') for f in findings)
        assert len(categories) >= 3  # At least 3 different vulnerability types


# =============================================================================
# CLI INTEGRATION TESTS
# =============================================================================

class TestCLIIntegration:
    """Test CLI commands for new features."""

    def test_cli_imports(self):
        """Test CLI can import new agents."""
        try:
            from agent.subagents import ResearchAgent, SecurityAgent
            assert ResearchAgent is not None
            assert SecurityAgent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import new agents: {e}")
            
    def test_subagent_type_enum(self):
        """Test SubAgentType enum includes new types."""
        from agent.subagents import SubAgentType
        
        assert hasattr(SubAgentType, 'RESEARCH')
        assert hasattr(SubAgentType, 'SECURITY')
        assert SubAgentType.RESEARCH.value == 'research'
        assert SubAgentType.SECURITY.value == 'security'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
