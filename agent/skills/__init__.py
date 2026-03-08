"""Skills package for RapidWebs Agent.

This package contains modular skills that extend agent capabilities:
- terminal_executor: Shell command execution
- web_scraper: Web content fetching
- filesystem: File operations
- search: Codebase search
- code_tools: Linting and formatting
- git: Git version control
"""

# Import SkillBase from skills_manager for backward compatibility
from agent.skills_manager import SkillBase

# Import GitSkill
from .git_skill import GitSkill

__all__ = ['GitSkill', 'SkillBase']
