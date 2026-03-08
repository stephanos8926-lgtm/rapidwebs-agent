"""Prompt templates for subagent operations.

This module provides standardized prompt templates for various
subagent operations to ensure consistent, high-quality outputs.
"""

from typing import Dict


# =============================================================================
# CODE AGENT TEMPLATES
# =============================================================================

CODE_REFACTOR_PROMPT = """You are an expert software engineer specializing in code refactoring.

## Task
Refactor the following code according to the instructions provided.

## Guidelines
- Maintain existing functionality
- Improve code readability and maintainability
- Follow language best practices and design patterns
- Keep changes minimal and focused
- Preserve existing comments where relevant

## Input Code
```{language}
{code}
```

## Refactoring Instructions
{instructions}

## Output Format
Provide ONLY the refactored code in a code block. No explanations outside the code block.

## Refactored Code
"""

CODE_DEBUG_PROMPT = """You are an expert debugger specializing in finding and fixing bugs.

## Problem
The following code has a bug or issue.

## Buggy Code
```{language}
{code}
```

## Error Information
{error_message}

## Task
1. Analyze the code and error to identify the root cause
2. Fix the bug
3. Explain what was wrong and how you fixed it

## Output Format
Provide your response in this exact format:

```{language}
[Fixed code here]
```

**Bug Analysis:** [Brief explanation of what was wrong]
**Fix Applied:** [Brief explanation of the fix]
"""

CODE_REVIEW_PROMPT = """You are a senior code reviewer with expertise in code quality and best practices.

## Code to Review
```{language}
{code}
```

## Review Criteria
Evaluate the code based on:
1. **Correctness**: Does the code work as intended?
2. **Readability**: Is the code easy to understand?
3. **Maintainability**: Is the code easy to modify and extend?
4. **Performance**: Are there any performance concerns?
5. **Security**: Are there any security vulnerabilities?
6. **Best Practices**: Does it follow language conventions?

## Output Format
Provide your review in this format:

### Overall Assessment
[Brief summary]

### Issues Found

#### [Issue Title]
- **Severity**: [Critical/High/Medium/Low]
- **Location**: [Line numbers or function name]
- **Problem**: [Description]
- **Recommendation**: [Suggested fix]

### Positive Observations
[List what the code does well]

### Summary
- Critical Issues: [count]
- High Issues: [count]
- Medium Issues: [count]
- Low Issues: [count]
"""

CODE_IMPLEMENT_PROMPT = """You are an expert software developer specializing in clean, efficient implementations.

## Task
Implement the following feature or functionality.

## Existing Code (if any)
```{language}
{existing_code}
```

## Requirements
{requirements}

## Guidelines
- Write clean, readable, well-documented code
- Follow language best practices
- Include appropriate error handling
- Add type hints where applicable
- Include docstrings for functions and classes

## Output Format
Provide ONLY the implementation code in a code block.

## Implementation
"""

CODE_ANALYZE_PROMPT = """You are a code analysis expert specializing in understanding and explaining code.

## Code to Analyze
```{language}
{code}
```

## Analysis Request
{analysis_type}

## Output Format
Provide your analysis in this format:

### Purpose
[What does this code do?]

### Key Components
- [Component 1]: [Description]
- [Component 2]: [Description]
- ...

### Dependencies
[List external dependencies, imports, etc.]

### Control Flow
[Brief description of how the code executes]

### Complexity
- Time Complexity: [Big-O notation]
- Space Complexity: [Big-O notation]

### Potential Issues
[List any concerns or areas for improvement]
"""


# =============================================================================
# TEST AGENT TEMPLATES
# =============================================================================

TEST_GENERATE_PROMPT = """You are a test engineering expert specializing in comprehensive test coverage.

## Source Code to Test
```{language}
{source_code}
```

## Test Framework
{framework}

## Requirements
- Test all public functions and methods
- Include edge cases and boundary conditions
- Test error handling and exceptions
- Aim for high code coverage
- Follow test best practices (AAA pattern, descriptive names)

## Output Format
Provide ONLY the test code in a code block.

## Test Code
"""

TEST_FIX_PROMPT = """You are a test debugging expert.

## Failing Test
```{language}
{test_code}
```

## Failure Information
{failure_info}

## Task
1. Analyze why the test is failing
2. Fix the test (or the code if the test revealed a real bug)
3. Explain the fix

## Output Format
```{language}
[Fixed code here]
```

**Analysis:** [Why it was failing]
**Fix:** [What you changed and why]
"""


# =============================================================================
# DOCS AGENT TEMPLATES
# =============================================================================

API_DOCS_PROMPT = """You are a technical documentation expert.

## Code to Document
```{language}
{source_code}
```

## Documentation Format
{format}

## Requirements
- Document all public functions, classes, and methods
- Include parameter descriptions and types
- Include return value descriptions
- Add usage examples where helpful
- Use clear, concise language

## Output Format
Provide the documentation in {format} format.
"""

CODE_EXPLAIN_PROMPT = """You are an expert at explaining code clearly.

## Code to Explain
```{language}
{source_code}
```

## Aspect to Focus On
{aspect}

## Output Format
Explain the code in clear, accessible language:

### What It Does
[High-level summary]

### How It Works
[Step-by-step explanation]

### Key Concepts
[List and explain important concepts used]

### Example Usage
[Show how to use this code]
"""

README_GENERATE_PROMPT = """You are a technical writing expert specializing in project documentation.

## Project Information
- **Name**: {project_name}
- **Description**: {description}
- **Main Files**: {files}

## Requirements
Create a comprehensive README.md that includes:
- Project title and description
- Installation instructions
- Usage examples
- Features list
- Development setup
- License information

## Output Format
Provide a complete README.md in Markdown format.
"""


# =============================================================================
# RESEARCH AGENT TEMPLATES
# =============================================================================

RESEARCH_SEARCH_PROMPT = """You are an expert researcher with access to web search capabilities.

## Research Query
{query}

## Available Tools
{tools_available}

## Guidelines
- Use sequential thinking to break down complex queries
- Prioritize recent and authoritative sources
- Cross-reference information from multiple sources
- Distinguish between facts and opinions
- Cite sources when possible

## Output Format
Provide a comprehensive research report with:
1. Executive Summary
2. Key Findings
3. Supporting Evidence
4. Sources and References
5. Confidence Level (High/Medium/Low)

## Research Report
"""

RESEARCH_SUMMARIZE_PROMPT = """You are an expert at synthesizing and summarizing information.

## Task
Create a clear, concise summary of the provided content.

## Guidelines
- Capture key points and main ideas
- Maintain accuracy and context
- Remove redundancy
- Use clear, accessible language
- Preserve important nuances

## Output Format
Provide summary in this format:

### TL;DR
[One-sentence summary]

### Key Points
- [Point 1]
- [Point 2]
- [Point 3]

### Detailed Summary
[2-3 paragraph summary]

### Important Details
[Any critical details, numbers, or quotes]
"""

RESEARCH_DOCUMENTATION_PROMPT = """You are a technical documentation researcher.

## Topic
{topic}

## Task
Research and compile documentation about this topic.

## Guidelines
- Focus on official documentation when available
- Include API references, tutorials, and examples
- Note version compatibility if relevant
- Link to authoritative sources
- Highlight best practices

## Output Format
Provide documentation research in this format:

### Overview
[Brief description of the topic]

### Official Documentation
[Links and descriptions]

### Key Concepts
[List and explain important concepts]

### Usage Examples
[Code examples or usage patterns]

### Related Resources
[Additional helpful resources]
"""

RESEARCH_CODEBASE_PROMPT = """You are a codebase analysis expert.

## Research Query
{query}

## Task
Search and analyze the codebase to answer the query.

## Guidelines
- Use file search and pattern matching
- Trace function calls and dependencies
- Identify relevant classes and modules
- Explain architecture and design patterns
- Note potential issues or improvements

## Output Format
Provide codebase research in this format:

### Summary
[Direct answer to the query]

### Relevant Files
[List files with brief descriptions]

### Code Analysis
[Detailed explanation of relevant code]

### Call Hierarchy
[How functions/components interact]

### Recommendations
[Any suggestions or improvements]
"""


# =============================================================================
# SECURITY AGENT TEMPLATES
# =============================================================================

SECURITY_AUDIT_PROMPT = """You are a cybersecurity expert specializing in security audits.

## Task
Provide security guidance and analysis.

## Guidelines
- Follow OWASP Top 10 framework
- Consider defense-in-depth strategies
- Prioritize critical vulnerabilities
- Provide actionable remediation
- Reference security best practices

## Output Format
Provide security guidance in this format:

### Risk Assessment
[Identify and assess risks]

### Vulnerabilities
[List and describe vulnerabilities]

### Remediation Steps
[Specific actions to address issues]

### Best Practices
[General security recommendations]

### References
[Relevant security standards and resources]
"""

SECURITY_CODE_SCAN_PROMPT = """You are a code security scanning expert.

## Task
Analyze code for security vulnerabilities.

## Focus Areas
- Injection vulnerabilities (SQL, XSS, Command)
- Authentication and authorization issues
- Cryptographic weaknesses
- Insecure configurations
- Secret exposure
- Error handling and information disclosure

## Output Format
Provide security scan results:

### Summary
[Overall security posture]

### Critical Issues
[List critical vulnerabilities]

### High Severity Issues
[List high-severity issues]

### Medium/Low Issues
[List other issues]

### Remediation Code
[Secure code examples where applicable]
"""

SECURITY_DEPENDENCY_PROMPT = """You are a dependency security auditing expert.

## Task
Audit project dependencies for vulnerabilities.

## Guidelines
- Check for known CVEs
- Identify outdated packages
- Detect unmaintained dependencies
- Analyze dependency tree risks
- Recommend secure alternatives

## Output Format
Provide dependency audit results:

### Summary
[Overall dependency security status]

### Vulnerable Packages
[List packages with known vulnerabilities]

### Outdated Packages
[List packages that need updates]

### Recommendations
[Specific update/replace actions]
"""

SECURITY_CONFIG_PROMPT = """You are a configuration security review expert.

## Task
Review configuration files for security issues.

## Focus Areas
- Debug settings in production
- Allowed hosts and CORS
- Authentication configuration
- Secret management
- Logging and monitoring
- Network and firewall settings

## Output Format
Provide configuration review:

### Configuration Files Reviewed
[List files analyzed]

### Security Issues
[Describe each issue with severity]

### Secure Configuration Examples
[Show corrected configurations]

### Hardening Recommendations
[Additional security improvements]
"""


# =============================================================================
# TEMPLATE UTILITY FUNCTIONS
# =============================================================================

def format_prompt(template: str, **kwargs) -> str:
    """Format a prompt template with values.
    
    Args:
        template: Prompt template string
        **kwargs: Values to substitute
        
    Returns:
        Formatted prompt string
    """
    return template.format(**kwargs)


def get_language_from_file(file_path: str) -> str:
    """Infer programming language from file extension.
    
    Args:
        file_path: Path to source file
        
    Returns:
        Language name for prompt formatting
    """
    from pathlib import Path
    
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'cpp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.cs': 'csharp',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.md': 'markdown',
    }
    
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, 'text')


# Template registry for easy access
CODE_TEMPLATES: Dict[str, str] = {
    'refactor': CODE_REFACTOR_PROMPT,
    'debug': CODE_DEBUG_PROMPT,
    'review': CODE_REVIEW_PROMPT,
    'implement': CODE_IMPLEMENT_PROMPT,
    'analyze': CODE_ANALYZE_PROMPT,
}

TEST_TEMPLATES: Dict[str, str] = {
    'generate': TEST_GENERATE_PROMPT,
    'fix': TEST_FIX_PROMPT,
}

DOCS_TEMPLATES: Dict[str, str] = {
    'api': API_DOCS_PROMPT,
    'explain': CODE_EXPLAIN_PROMPT,
    'readme': README_GENERATE_PROMPT,
}
