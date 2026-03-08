"""Security Agent for security auditing and vulnerability detection.

This subagent specializes in security tasks including:
- Dependency vulnerability scanning
- Code security analysis
- Configuration security review
- OWASP Top 10 vulnerability detection
- Secret and credential detection
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from .protocol import (
    SubAgentProtocol, SubAgentTask, SubAgentResult, SubAgentStatus,
    SubAgentConfig, SubAgentType
)
from .prompts import (
    SECURITY_AUDIT_PROMPT, SECURITY_CONFIG_PROMPT
)


# OWASP Top 10 2021 patterns
OWASP_PATTERNS = {
    'A01_BrokenAccessControl': [
        r'if\s*\(.*is_admin.*\)',
        r'if\s*\(.*role\s*==.*admin.*\)',
        r'@app\.route\s*\([^)]*methods\s*=\s*\[.*DELETE.*\]',
    ],
    'A02_CryptographicFailures': [
        r'md5\s*\(',
        r'sha1\s*\(',
        r'DES\s*\(',
        r'ECB',
        r'password\s*=\s*["\'][^"\']+["\']',
    ],
    'A03_Injection': [
        r'execute\s*\(\s*["\'].*%s',
        r'cursor\.execute\s*\(\s*f["\']',
        r'eval\s*\(',
        r'exec\s*\(',
        r'os\.system\s*\(',
        r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
    ],
    'A04_InsecureDesign': [
        r'rate.*limit.*=.*False',
        r'throttle.*=.*False',
    ],
    'A05_SecurityMisconfiguration': [
        r'DEBUG\s*=\s*True',
        r'debug\s*=\s*True',
        r'ALLOWED_HOSTS\s*=\s*\[\s*["\']\*["\']',
    ],
    'A06_VulnerableComponents': [
        # Detected via dependency scanning
    ],
    'A07_AuthFailure': [
        r'authenticate.*=.*False',
        r'verify.*=.*False',
        r'password.*==.*password',
        r'if\s+password\s*==',
    ],
    'A08_DataIntegrity': [
        r'disable.*checksum',
        r'verify.*=.*False',
    ],
    'A09_LoggingFailures': [
        r'logging\.disable',
        r'log.*=.*False',
    ],
    'A10_SSRF': [
        r'requests\.get\s*\([^)]*user_input',
        r'urllib\.request\.urlopen\s*\([^)]*user',
        r'fetch.*url.*from.*request',
    ],
}

# Secret detection patterns (optimized to reduce false positives)
SECRET_PATTERNS = {
    'AWS Access Key': r'AKIA[0-9A-Z]{16}',
    'AWS Secret Key': r'(?:aws_secret_access_key|AWS_SECRET_KEY|aws_secret_key)\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
    'GitHub Token': r'gh[pousr]_[A-Za-z0-9_]{36,}',
    'Google API Key': r'AIza[0-9A-Za-z_-]{35}',
    'Private Key': r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
    'Generic API Key': r'(?:api[_-]?key|apikey|API_KEY)\s*[=:]\s*["\'][^"\']{8,}["\']',
    'Generic Secret': r'(?:secret[_-]?key|secret_key|SECRET_KEY)\s*[=:]\s*["\'][^"\']{8,}["\']',
    'Password in Code': r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{4,}["\']',
    'Bearer Token': r'[Bb]earer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+',
    'Slack Token': r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*',
    'Stripe Key': r'sk_live_[0-9a-zA-Z]{24,}',
}

# Dependency file patterns
DEPENDENCY_FILES = {
    'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
    'node': ['package.json', 'package-lock.json', 'yarn.lock'],
    'ruby': ['Gemfile', 'Gemfile.lock'],
    'rust': ['Cargo.toml', 'Cargo.lock'],
    'go': ['go.mod', 'go.sum'],
    'php': ['composer.json', 'composer.lock'],
}


class SecurityAgent(SubAgentProtocol):
    """SubAgent for security auditing and vulnerability detection.

    This agent handles:
    - Dependency vulnerability scanning
    - Code security analysis (OWASP Top 10)
    - Configuration security review
    - Secret and credential detection
    - Security report generation
    """

    def __init__(self, config: SubAgentConfig = None, model_manager=None):
        """Initialize Security Agent.

        Args:
            config: Agent configuration (uses defaults if None)
            model_manager: ModelManager for LLM integration
        """
        if config is None:
            config = SubAgentConfig(
                type=SubAgentType.SECURITY,
                enabled=True,
                max_token_budget=20000,
                max_timeout=900,
                allowed_tools=[
                    'read_file', 'search_files', 'write_file',
                    'list_directory', 'read_multiple_files'
                ],
                parallel_limit=2
            )
        super().__init__(config, model_manager)

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.

        Returns:
            Dictionary describing capabilities
        """
        caps = super().get_capabilities()
        caps['specialties'] = [
            'dependency_audit',
            'code_scanning',
            'config_review',
            'secret_detection',
            'owasp_top_10',
            'security_reporting'
        ]
        caps['scanners'] = {
            'dependencies': 'Vulnerability scanning for package dependencies',
            'code': 'Static analysis for security vulnerabilities',
            'config': 'Security configuration review',
            'secrets': 'Credential and secret detection',
        }
        caps['severity_levels'] = ['critical', 'high', 'medium', 'low', 'info']
        return caps

    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a security audit task.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        start_time = asyncio.get_event_loop().time()
        files_modified = []

        try:
            # Classify task type
            task_type = self._classify_task(task)

            if task_type == 'dependency_audit':
                result = await self._execute_dependency_audit(task)
            elif task_type == 'code_scan':
                result = await self._execute_code_scan(task)
            elif task_type == 'config_review':
                result = await self._execute_config_review(task)
            elif task_type == 'secret_scan':
                result = await self._execute_secret_scan(task)
            elif task_type == 'full_audit':
                result = await self._execute_full_audit(task)
            else:
                result = await self._execute_general_security(task)

            # Collect modified files
            if 'files_modified' in result:
                files_modified = result['files_modified']

            duration = asyncio.get_event_loop().time() - start_time

            return SubAgentResult(
                task_id=task.id,
                status=result.get('status', SubAgentStatus.COMPLETED),
                output=result.get('output', ''),
                token_usage=result.get('token_usage', 0),
                duration=duration,
                error=result.get('error'),
                metadata=result.get('metadata', {}),
                files_modified=files_modified
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            return SubAgentResult(
                task_id=task.id,
                status=SubAgentStatus.FAILED,
                output="",
                error=str(e),
                duration=duration,
                files_modified=files_modified
            )

    def _classify_task(self, task: SubAgentTask) -> str:
        """Classify task type from description and context.

        Args:
            task: Task to classify

        Returns:
            Task type string
        """
        description = task.description.lower()
        context = task.context

        # Check explicit type in context
        if 'type' in context:
            return context['type']

        # Classify by keywords (order matters - check specific phrases first)
        full_audit_keywords = ['full', 'comprehensive', 'complete security',
                              'security review', 'pentest']
        code_scan_keywords = ['scan code', 'security scan', 'vulnerability scan',
                             'owasp', 'injection', 'xss', 'csrf']
        secret_keywords = ['secret', 'credential', 'api key', 'password',
                          'token', 'leak', 'exposed']
        config_keywords = ['config', 'configuration', 'settings', 'environment',
                          '.env', 'docker', 'nginx', 'apache']
        dependency_keywords = ['dependenc', 'package', 'vulnerabilit', 'cve',
                              'outdated', 'requirements', 'package.json']

        # Check full audit first (most general)
        for keyword in full_audit_keywords:
            if keyword in description:
                return 'full_audit'

        # Then check specific task types
        for keyword in code_scan_keywords:
            if keyword in description:
                return 'code_scan'

        for keyword in secret_keywords:
            if keyword in description:
                return 'secret_scan'

        for keyword in config_keywords:
            if keyword in description:
                return 'config_review'

        for keyword in dependency_keywords:
            if keyword in description:
                return 'dependency_audit'

        return 'general'

    def _scan_for_secrets(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scan content for secrets and credentials.

        Args:
            content: File content to scan
            file_path: Optional file path for context

        Returns:
            List of detected secrets
        """
        findings = []

        for secret_type, pattern in SECRET_PATTERNS.items():
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Calculate line number
                line_num = content[:match.start()].count('\n') + 1

                # Mask the secret
                matched_text = match.group(0)
                if len(matched_text) > 10:
                    masked = matched_text[:5] + '***' + matched_text[-3:]
                else:
                    masked = matched_text[:3] + '***'

                findings.append({
                    'type': 'secret',
                    'severity': 'critical',
                    'category': secret_type,
                    'file': file_path,
                    'line': line_num,
                    'value': masked,
                    'raw_match': matched_text,
                    'message': f"Potential {secret_type} detected"
                })

        return findings

    def _scan_for_owasp(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scan content for OWASP Top 10 vulnerabilities.

        Args:
            content: File content to scan
            file_path: Optional file path for context

        Returns:
            List of detected vulnerabilities
        """
        findings = []

        for vuln_type, patterns in OWASP_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1

                    findings.append({
                        'type': 'owasp',
                        'severity': self._get_owasp_severity(vuln_type),
                        'category': vuln_type,
                        'file': file_path,
                        'line': line_num,
                        'pattern': pattern,
                        'message': f"Potential {vuln_type} vulnerability"
                    })

        return findings

    def _get_owasp_severity(self, vuln_type: str) -> str:
        """Get severity for OWASP vulnerability type.

        Args:
            vuln_type: OWASP vulnerability type

        Returns:
            Severity string
        """
        high_severity = [
            'A01_BrokenAccessControl',
            'A02_CryptographicFailures',
            'A03_Injection',
            'A07_AuthFailure'
        ]
        medium_severity = [
            'A04_InsecureDesign',
            'A05_SecurityMisconfiguration',
            'A08_DataIntegrity',
            'A10_SSRF'
        ]

        if vuln_type in high_severity:
            return 'high'
        elif vuln_type in medium_severity:
            return 'medium'
        else:
            return 'low'

    async def _find_dependency_files(self, workspace: Path = None) -> Dict[str, List[Path]]:
        """Find dependency files in workspace.

        Args:
            workspace: Workspace root path

        Returns:
            Dictionary mapping language to list of dependency files
        """
        if workspace is None:
            workspace = Path.cwd()

        found_files = {lang: [] for lang in DEPENDENCY_FILES.keys()}

        # Search for dependency files
        for lang, patterns in DEPENDENCY_FILES.items():
            for pattern in patterns:
                for file_path in workspace.rglob(pattern):
                    # Skip node_modules and .venv
                    if 'node_modules' in str(file_path) or '.venv' in str(file_path):
                        continue
                    found_files[lang].append(file_path)

        return found_files

    async def _execute_dependency_audit(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute dependency vulnerability audit.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        workspace = Path(task.context.get('workspace', Path.cwd()))
        target_lang = task.context.get('language', 'python')

        # Find dependency files
        dep_files = await self._find_dependency_files(workspace)

        if not dep_files.get(target_lang, []):
            return {
                'status': SubAgentStatus.COMPLETED,
                'output': f"No {target_lang} dependency files found in {workspace}",
                'token_usage': 0,
                'metadata': {
                    'scan_type': 'dependency_audit',
                    'language': target_lang,
                    'files_scanned': 0,
                    'vulnerabilities': []
                },
                'files_modified': []
            }

        # Read dependency files and analyze
        findings = []
        files_scanned = []

        for dep_file in dep_files[target_lang]:
            try:
                with open(dep_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                files_scanned.append(str(dep_file))

                # Parse dependencies and check for known vulnerabilities
                deps = self._parse_dependencies(content, target_lang)
                for dep_name, version in deps.items():
                    # Check for known vulnerable patterns
                    vuln_check = self._check_dependency_vulnerability(dep_name, version)
                    if vuln_check:
                        findings.append(vuln_check)

            except (OSError, IOError) as e:
                findings.append({
                    'type': 'error',
                    'severity': 'info',
                    'file': str(dep_file),
                    'message': f"Failed to read dependency file: {str(e)}"
                })
            except Exception as e:
                findings.append({
                    'type': 'error',
                    'severity': 'info',
                    'file': str(dep_file),
                    'message': f"Error processing dependency file: {str(e)}"
                })

        # Generate report
        report = self._generate_dependency_report(findings, files_scanned, target_lang)

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': report,
            'token_usage': 0,  # Pattern-based, no LLM
            'metadata': {
                'scan_type': 'dependency_audit',
                'language': target_lang,
                'files_scanned': len(files_scanned),
                'vulnerabilities': findings,
                'severity_counts': self._count_severities(findings)
            },
            'files_modified': []
        }

    def _parse_dependencies(self, content: str, lang: str) -> Dict[str, str]:
        """Parse dependencies from file content with robust error handling.

        Args:
            content: Dependency file content
            lang: Programming language

        Returns:
            Dictionary mapping package name to version
        """
        dependencies: Dict[str, str] = {}

        if lang == 'python':
            # Parse requirements.txt format
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Handle various formats: pkg==1.0, pkg>=1.0, pkg~=1.0
                    match = re.match(r'^([a-zA-Z0-9_-]+)([=<>~!]+)?(.+)?$', line)
                    if match:
                        pkg_name = match.group(1)
                        version = match.group(3) or 'latest'
                        dependencies[pkg_name] = version

        elif lang == 'node':
            # Parse package.json format (simplified)
            try:
                import json
                data = json.loads(content)
                if not isinstance(data, dict):
                    return dependencies
                    
                for pkg_type in ['dependencies', 'devDependencies']:
                    if pkg_type in data and isinstance(data[pkg_type], dict):
                        for pkg, ver in data[pkg_type].items():
                            if isinstance(pkg, str) and isinstance(ver, str):
                                dependencies[pkg] = ver
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError):
                pass  # Return empty dependencies on parse error

        return dependencies

    def _check_dependency_vulnerability(self, name: str, version: str) -> Optional[Dict[str, Any]]:
        """Check if dependency has known vulnerabilities.

        Args:
            name: Package name
            version: Package version

        Returns:
            Vulnerability info or None
        """
        # Common vulnerable packages (simplified check)
        vulnerable_packages = {
            'requests': {'versions': ['<2.31.0'], 'cve': 'CVE-2023-32681', 'severity': 'medium'},
            'flask': {'versions': ['<2.3.2'], 'cve': 'CVE-2023-30861', 'severity': 'high'},
            'django': {'versions': ['<4.2.4'], 'cve': 'CVE-2023-41164', 'severity': 'high'},
            'lodash': {'versions': ['<4.17.21'], 'cve': 'CVE-2021-23337', 'severity': 'high'},
            'express': {'versions': ['<4.18.2'], 'cve': 'CVE-2022-24999', 'severity': 'medium'},
        }

        if name.lower() in vulnerable_packages:
            vuln_info = vulnerable_packages[name.lower()]
            # Simplified version check
            return {
                'type': 'vulnerable_dependency',
                'severity': vuln_info['severity'],
                'package': name,
                'version': version,
                'cve': vuln_info['cve'],
                'message': f"Package {name}@{version} may have known vulnerabilities ({vuln_info['cve']})"
            }

        return None

    def _generate_dependency_report(self, findings: List[Dict], files: List[str], lang: str) -> str:
        """Generate dependency audit report.

        Args:
            findings: List of findings
            files: List of scanned files
            lang: Programming language

        Returns:
            Report string
        """
        report = "# Dependency Security Audit Report\n\n"
        report += f"**Language:** {lang}\n"
        report += f"**Files Scanned:** {len(files)}\n\n"

        if not findings:
            report += "✅ No known vulnerabilities detected!\n\n"
        else:
            severity_counts = self._count_severities(findings)
            report += "## Summary\n\n"
            report += f"- 🔴 Critical: {severity_counts.get('critical', 0)}\n"
            report += f"- 🟠 High: {severity_counts.get('high', 0)}\n"
            report += f"- 🟡 Medium: {severity_counts.get('medium', 0)}\n"
            report += f"- 🟢 Low: {severity_counts.get('low', 0)}\n\n"

            report += "## Findings\n\n"
            for i, finding in enumerate(findings, 1):
                report += f"### {i}. {finding.get('message', 'Unknown')}\n"
                report += f"- **Severity:** {finding.get('severity', 'unknown')}\n"
                report += f"- **Package:** {finding.get('package', 'N/A')}\n"
                if 'cve' in finding:
                    report += f"- **CVE:** {finding['cve']}\n"
                report += "\n"

        return report

    def _count_severities(self, findings: List[Dict]) -> Dict[str, int]:
        """Count findings by severity.

        Args:
            findings: List of findings

        Returns:
            Dictionary mapping severity to count
        """
        counts = {}
        for finding in findings:
            severity = finding.get('severity', 'unknown')
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    async def _execute_code_scan(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code security scan.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        workspace = Path(task.context.get('workspace', Path.cwd()))
        target_file = task.context.get('file')

        findings = []
        files_scanned = []

        if target_file:
            # Scan specific file
            file_path = Path(target_file)
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    files_scanned.append(str(file_path))
                    findings.extend(self._scan_for_secrets(content, str(file_path)))
                    findings.extend(self._scan_for_owasp(content, str(file_path)))
                except Exception as e:
                    findings.append({
                        'type': 'error',
                        'severity': 'info',
                        'file': str(file_path),
                        'message': f"Failed to scan file: {str(e)}"
                    })
        else:
            # Scan workspace (limit to code files)
            code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb']
            for ext in code_extensions:
                for file_path in workspace.rglob(f'*{ext}'):
                    # Skip test files and dependencies
                    if 'test' in str(file_path) or 'node_modules' in str(file_path):
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        files_scanned.append(str(file_path))
                        findings.extend(self._scan_for_secrets(content, str(file_path)))
                        findings.extend(self._scan_for_owasp(content, str(file_path)))
                    except Exception:
                        pass  # Skip files that can't be read

        # Generate report
        report = self._generate_code_scan_report(findings, files_scanned)

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': report,
            'token_usage': 0,
            'metadata': {
                'scan_type': 'code_scan',
                'files_scanned': len(files_scanned),
                'vulnerabilities': findings,
                'severity_counts': self._count_severities(findings)
            },
            'files_modified': []
        }

    def _generate_code_scan_report(self, findings: List[Dict], files: List[str]) -> str:
        """Generate code scan report.

        Args:
            findings: List of findings
            files: List of scanned files

        Returns:
            Report string
        """
        report = "# Code Security Scan Report\n\n"
        report += f"**Files Scanned:** {len(files)}\n\n"

        if not findings:
            report += "✅ No security issues detected!\n\n"
        else:
            severity_counts = self._count_severities(findings)
            report += "## Summary\n\n"
            report += f"- 🔴 Critical: {severity_counts.get('critical', 0)}\n"
            report += f"- 🟠 High: {severity_counts.get('high', 0)}\n"
            report += f"- 🟡 Medium: {severity_counts.get('medium', 0)}\n"
            report += f"- 🟢 Low: {severity_counts.get('low', 0)}\n\n"

            # Group by severity
            for severity in ['critical', 'high', 'medium', 'low']:
                severity_findings = [f for f in findings if f.get('severity') == severity]
                if severity_findings:
                    report += f"## {severity.upper()} Severity Issues\n\n"
                    for i, finding in enumerate(severity_findings, 1):
                        report += f"### {i}. {finding.get('message', 'Unknown')}\n"
                        report += f"- **File:** {finding.get('file', 'N/A')}\n"
                        report += f"- **Line:** {finding.get('line', 'N/A')}\n"
                        report += f"- **Category:** {finding.get('category', 'N/A')}\n\n"

        return report

    async def _execute_config_review(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute configuration security review.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        # Use LLM for intelligent config review
        config_files = task.context.get('files', [])
        config_content = ""

        for file_path in config_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                config_content += f"\n\n# File: {file_path}\n{content}"
            except Exception as e:
                config_content += f"\n\n# File: {file_path}\nError reading: {e}"

        system_prompt = SECURITY_CONFIG_PROMPT

        try:
            response, tokens = await self._call_llm(
                f"Review these configuration files for security issues:\n{config_content}",
                system_prompt
            )

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'scan_type': 'config_review',
                    'files_reviewed': config_files
                },
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"Config review failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }

    async def _execute_secret_scan(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute secret and credential scan.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        workspace = Path(task.context.get('workspace', Path.cwd()))

        findings = []
        files_scanned = []

        # Scan common file types for secrets
        scan_extensions = ['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.txt', '.md']
        for ext in scan_extensions:
            for file_path in workspace.rglob(f'*{ext}'):
                # Skip .venv, node_modules, .git
                skip_dirs = ['.venv', 'node_modules', '.git', '__pycache__']
                if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    files_scanned.append(str(file_path))
                    findings.extend(self._scan_for_secrets(content, str(file_path)))
                except Exception:
                    pass

        # Generate report
        report = self._generate_secret_scan_report(findings, files_scanned)

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': report,
            'token_usage': 0,
            'metadata': {
                'scan_type': 'secret_scan',
                'files_scanned': len(files_scanned),
                'secrets_found': len(findings),
                'findings': findings
            },
            'files_modified': []
        }

    def _generate_secret_scan_report(self, findings: List[Dict], files: List[str]) -> str:
        """Generate secret scan report.

        Args:
            findings: List of findings
            files: List of scanned files

        Returns:
            Report string
        """
        report = "# Secret & Credential Scan Report\n\n"
        report += f"**Files Scanned:** {len(files)}\n\n"

        if not findings:
            report += "✅ No secrets or credentials detected!\n\n"
        else:
            report += f"## 🚨 CRITICAL: {len(findings)} Secrets Detected\n\n"

            # Group by type
            by_type = {}
            for finding in findings:
                secret_type = finding.get('category', 'Unknown')
                if secret_type not in by_type:
                    by_type[secret_type] = []
                by_type[secret_type].append(finding)

            for secret_type, type_findings in by_type.items():
                report += f"### {secret_type} ({len(type_findings)} found)\n\n"
                for i, finding in enumerate(type_findings, 1):
                    report += f"{i}. **File:** `{finding['file']}` (Line {finding['line']})\n"
                    report += f"   **Value:** `{finding['value']}`\n\n"

            report += "⚠️ **IMPORTANT:** Rotate all exposed credentials immediately!\n"

        return report

    async def _execute_full_audit(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute comprehensive security audit.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        # Run all scans
        all_findings = []

        # 1. Dependency audit
        dep_result = await self._execute_dependency_audit(task)
        if dep_result.get('metadata', {}).get('vulnerabilities'):
            all_findings.extend(dep_result['metadata']['vulnerabilities'])

        # 2. Code scan
        code_result = await self._execute_code_scan(task)
        if code_result.get('metadata', {}).get('vulnerabilities'):
            all_findings.extend(code_result['metadata']['vulnerabilities'])

        # 3. Secret scan
        secret_result = await self._execute_secret_scan(task)
        if secret_result.get('metadata', {}).get('findings'):
            all_findings.extend(secret_result['metadata']['findings'])

        # Generate comprehensive report
        report = self._generate_full_audit_report(all_findings, task)

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': report,
            'token_usage': 0,
            'metadata': {
                'scan_type': 'full_audit',
                'total_findings': len(all_findings),
                'severity_counts': self._count_severities(all_findings)
            },
            'files_modified': []
        }

    def _generate_full_audit_report(self, findings: List[Dict], task: SubAgentTask) -> str:
        """Generate comprehensive audit report.

        Args:
            findings: List of all findings
            task: Original task

        Returns:
            Report string
        """
        report = "# 🔒 Comprehensive Security Audit Report\n\n"
        report += f"**Task:** {task.description}\n"
        report += f"**Date:** {asyncio.get_event_loop().time()}\n\n"

        severity_counts = self._count_severities(findings)

        report += "## Executive Summary\n\n"
        total = len(findings)
        if total == 0:
            report += "✅ **No security issues detected!**\n\n"
        else:
            report += f"🚨 **Total Issues:** {total}\n\n"
            report += f"- 🔴 Critical: {severity_counts.get('critical', 0)}\n"
            report += f"- 🟠 High: {severity_counts.get('high', 0)}\n"
            report += f"- 🟡 Medium: {severity_counts.get('medium', 0)}\n"
            report += f"- 🟢 Low: {severity_counts.get('low', 0)}\n\n"

            # Prioritized recommendations
            report += "## 🎯 Priority Actions\n\n"
            if severity_counts.get('critical', 0) > 0:
                report += "### IMMEDIATE ACTION REQUIRED\n"
                report += "Address all critical findings before deploying to production.\n\n"

            if severity_counts.get('high', 0) > 0:
                report += "### HIGH PRIORITY\n"
                report += "Resolve high-severity issues within 24-48 hours.\n\n"

        report += "## Detailed Findings\n\n"
        # Group by type
        by_type = {}
        for finding in findings:
            ftype = finding.get('type', 'unknown')
            if ftype not in by_type:
                by_type[ftype] = []
            by_type[ftype].append(finding)

        for ftype, type_findings in by_type.items():
            report += f"### {ftype.replace('_', ' ').title()} ({len(type_findings)})\n\n"
            for finding in type_findings[:10]:  # Limit to first 10 per category
                report += f"- [{finding.get('severity', 'unknown').upper()}] {finding.get('message', 'N/A')}\n"
                report += f"  - File: `{finding.get('file', 'N/A')}`\n\n"

            if len(type_findings) > 10:
                report += f"... and {len(type_findings) - 10} more\n\n"

        return report

    async def _execute_general_security(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute general security task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        # Use LLM for general security guidance
        system_prompt = SECURITY_AUDIT_PROMPT

        try:
            response, tokens = await self._call_llm(task.description, system_prompt)

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'scan_type': 'general_security',
                    'topic': task.description
                },
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"General security task failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
