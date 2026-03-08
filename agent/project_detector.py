"""Project Type Detection and Enhanced Repo Mapping.

Analyzes workspace structure to detect project type and generate intelligent
project skeletons for better LLM context.

Features:
- Auto-detect project type (Python, Node.js, Go, Rust, etc.)
- Identify key files (README, config, entry points)
- Generate project skeleton with metadata
- Suggest missing tools based on project type
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict


@dataclass
class ProjectInfo:
    """Information about a detected project."""
    project_type: str = "unknown"
    name: str = ""
    version: str = ""
    description: str = ""
    entry_points: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    languages: Set[str] = field(default_factory=set)
    frameworks: Set[str] = field(default_factory=set)
    tools_needed: List[str] = field(default_factory=list)
    confidence: float = 0.0


class ProjectTypeDetector:
    """Detect project type and generate project skeleton."""

    # Project type signatures (key files that indicate project type)
    # Ordered by priority (higher priority types checked first)
    PROJECT_SIGNATURES = {
        'python': [
            ('pyproject.toml', 3), ('setup.py', 3), ('setup.cfg', 2), 
            ('requirements.txt', 2), ('requirements.in', 2),
            ('Pipfile', 2), ('Pipfile.lock', 1), ('poetry.lock', 2),
            ('.python-version', 1), ('MANIFEST.in', 1)
        ],
        'node': [
            ('package.json', 3), ('package-lock.json', 2), ('yarn.lock', 2), 
            ('pnpm-lock.yaml', 2), ('.npmrc', 1), ('.yarnrc', 1), 
            ('tsconfig.json', 1)
        ],
        'go': [
            ('go.mod', 3), ('go.sum', 2), ('Gopkg.toml', 2), 
            ('Gopkg.lock', 1), ('glide.yaml', 1), ('glide.lock', 1)
        ],
        'rust': [
            ('Cargo.toml', 3), ('Cargo.lock', 2), 
            ('rust-toolchain', 1), ('rust-toolchain.toml', 1)
        ],
        'java': [
            ('pom.xml', 3), ('build.gradle', 3), ('build.gradle.kts', 3), 
            ('settings.gradle', 2), ('settings.gradle.kts', 2), 
            ('gradlew', 2), ('gradlew.bat', 1)
        ],
        'ruby': [
            ('Gemfile', 3), ('Gemfile.lock', 2), ('Rakefile', 2), 
            ('.ruby-version', 1), ('.ruby-gemset', 1)
        ],
        'php': [
            ('composer.json', 3), ('composer.lock', 2), 
            ('phpunit.xml', 1), ('phpunit.xml.dist', 1)
        ],
        'dotnet': [
            ('*.csproj', 3), ('*.sln', 3), ('*.fsproj', 2), 
            ('*.vbproj', 2), ('global.json', 1)
        ],
        'swift': [
            ('Package.swift', 3), ('*.xcodeproj', 3), 
            ('*.xcworkspace', 2), ('Podfile', 2), ('Cartfile', 1)
        ],
        'dart': [
            ('pubspec.yaml', 3), ('pubspec.lock', 2)
        ],
        'elixir': [
            ('mix.exs', 3), ('mix.lock', 2)
        ],
        'haskell': [
            ('*.cabal', 3), ('stack.yaml', 2), ('cabal.project', 2)
        ],
        'cmake': [
            ('CMakeLists.txt', 3), ('CMakePresets.json', 1)
        ],
        'make': [
            ('Makefile', 3), ('makefile', 2), ('GNUmakefile', 2)
        ],
        'docker': [
            ('Dockerfile', 3), ('docker-compose.yml', 2), 
            ('docker-compose.yaml', 2), ('Containerfile', 2), 
            ('.dockerignore', 1)
        ],
        'kubernetes': [
            ('k8s/', 2), ('.kube/', 2), ('helm/', 2), 
            ('Chart.yaml', 3), ('values.yaml', 2)
        ],
        'terraform': [
            ('*.tf', 3), ('*.tfvars', 2), 
            ('.terraform.lock.hcl', 2), ('terraform.tfstate', 1)
        ],
    }
    
    # Documentation-only signatures (lower priority)
    DOC_SIGNATURES = {
        'markdown': [
            ('README.md', 1), ('CHANGELOG.md', 1), 
            ('CONTRIBUTING.md', 1), ('LICENSE', 1)
        ],
    }

    # Entry point patterns by project type
    ENTRY_POINTS = {
        'python': ['main.py', 'app.py', 'wsgi.py', 'asgi.py', 'manage.py', 'run.py'],
        'node': ['index.js', 'index.ts', 'app.js', 'app.ts', 'server.js', 'server.ts'],
        'go': ['main.go'],
        'rust': ['src/main.rs'],
        'java': ['src/main/java/*/Main.java', 'src/main/java/*/Application.java'],
        'ruby': ['bin/rails', 'bin/rake', 'app.rb', 'config.ru'],
        'php': ['public/index.php', 'index.php'],
        'dotnet': ['Program.cs', 'Startup.cs'],
        'swift': ['main.swift', 'AppDelegate.swift'],
        'dart': ['bin/*.dart', 'lib/*.dart'],
        'elixir': ['mix.exs'],
    }

    # Recommended tools by project type
    RECOMMENDED_TOOLS = {
        'python': ['ruff', 'black', 'mypy', 'pytest', 'pip-tools'],
        'node': ['prettier', 'eslint', 'typescript', 'jest', 'npm-check-updates'],
        'go': ['gofmt', 'goimports', 'golint', 'golangci-lint'],
        'rust': ['rustfmt', 'clippy', 'cargo-audit'],
        'java': ['checkstyle', 'pmd', 'spotbugs', 'mvn'],
        'ruby': ['rubocop', 'reek', 'brakeman'],
        'php': ['phpcs', 'phpstan', 'psalm', 'rector'],
        'terraform': ['tflint', 'terrascan', 'checkov'],
        'docker': ['hadolint'],
        'markdown': ['prettier', 'markdownlint'],
    }

    # Framework signatures (files/dirs that indicate frameworks)
    FRAMEWORK_SIGNATURES = {
        'python': {
            'django': ['manage.py', 'settings.py', 'wsgi.py'],
            'flask': ['app.py', 'wsgi.py', 'instance/'],
            'fastapi': ['main.py', 'app.py'],
            'pytest': ['pytest.ini', 'conftest.py', 'tests/'],
            'celery': ['celery.py', 'celeryconfig.py'],
        },
        'node': {
            'express': ['app.js', 'app.ts', 'routes/'],
            'react': ['src/index.jsx', 'src/App.jsx', 'public/index.html'],
            'vue': ['src/main.js', 'src/App.vue', 'public/index.html'],
            'angular': ['angular.json', 'src/app/'],
            'next': ['next.config.js', 'pages/', 'app/'],
            'nestjs': ['nest-cli.json', 'src/main.ts'],
            'jest': ['jest.config.js', 'jest.config.ts'],
        },
        'go': {
            'gin': ['main.go'],
            'echo': ['main.go'],
        },
        'rust': {
            'actix': ['src/main.rs'],
            'rocket': ['src/main.rs'],
        },
    }

    def detect(self, workspace: Path) -> ProjectInfo:
        """Detect project type and gather project information."""
        info = ProjectInfo()
        
        if not workspace.exists():
            return info
        
        # Scan for signature files with weighted scoring
        signatures_found: Dict[str, List[tuple]] = {}
        scores: Dict[str, int] = {}
        
        # Check main project signatures
        for project_type, signatures in self.PROJECT_SIGNATURES.items():
            found = []
            score = 0
            for sig, weight in signatures:
                if '*' in sig:
                    # Glob pattern
                    matches = list(workspace.glob(sig))
                    if matches:
                        found.extend((str(m.relative_to(workspace)), weight) for m in matches[:3])
                        score += weight * min(len(matches), 3)
                else:
                    # Exact file
                    if (workspace / sig).exists():
                        found.append((sig, weight))
                        score += weight
            
            if found:
                signatures_found[project_type] = found
                scores[project_type] = score
        
        # Check doc signatures (only if no main project type found)
        if not signatures_found:
            for project_type, signatures in self.DOC_SIGNATURES.items():
                found = []
                score = 0
                for sig, weight in signatures:
                    if (workspace / sig).exists():
                        found.append((sig, weight))
                        score += weight
                
                if found:
                    signatures_found[project_type] = found
                    scores[project_type] = score

        # Determine primary project type by score
        if scores:
            # Sort by score (higher = better match)
            sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            best_type = sorted_types[0][0]
            info.project_type = best_type
            info.key_files = [f[0] for f in signatures_found[best_type]]
            info.confidence = min(1.0, sorted_types[0][1] / 9.0)  # Normalize (9 = max reasonable score)
        
        # Detect languages from file extensions
        info.languages = self._detect_languages(workspace)
        
        # Detect frameworks
        info.frameworks = self._detect_frameworks(workspace, info.project_type)
        
        # Find entry points
        info.entry_points = self._find_entry_points(workspace, info.project_type)
        
        # Parse project metadata
        self._parse_metadata(workspace, info)
        
        # Get dependencies
        info.dependencies = self._get_dependencies(workspace, info.project_type)
        
        # Suggest tools
        info.tools_needed = self._suggest_tools(workspace, info.project_type)
        
        # Generate project name
        info.name = workspace.name or "unnamed-project"
        
        return info

    def _detect_languages(self, workspace: Path) -> Set[str]:
        """Detect programming languages from file extensions."""
        languages = set()
        
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.fs': 'fsharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.dart': 'dart',
            '.ex': 'elixir',
            '.exs': 'elixir',
            '.hs': 'haskell',
            '.clj': 'clojure',
            '.erl': 'erlang',
            '.sql': 'sql',
            '.sh': 'shell',
            '.bash': 'shell',
            '.zsh': 'shell',
            '.ps1': 'powershell',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.vue': 'vue',
            '.svelte': 'svelte',
            '.md': 'markdown',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.toml': 'toml',
            '.xml': 'xml',
        }
        
        for ext, lang in extension_map.items():
            if list(workspace.rglob(f'*{ext}')):
                languages.add(lang)
        
        return languages

    def _detect_frameworks(self, workspace: Path, project_type: str) -> Set[str]:
        """Detect frameworks from project structure."""
        frameworks = set()
        
        if project_type in self.FRAMEWORK_SIGNATURES:
            for framework, signatures in self.FRAMEWORK_SIGNATURES[project_type].items():
                for sig in signatures:
                    if sig.endswith('/'):
                        # Directory check
                        if (workspace / sig.rstrip('/')).exists():
                            frameworks.add(framework)
                            break
                    else:
                        # File check
                        if (workspace / sig).exists():
                            frameworks.add(framework)
                            break
        
        return frameworks

    def _find_entry_points(self, workspace: Path, project_type: str) -> List[str]:
        """Find project entry points."""
        entry_points = []
        
        if project_type in self.ENTRY_POINTS:
            for pattern in self.ENTRY_POINTS[project_type]:
                if '*' in pattern:
                    matches = list(workspace.glob(pattern))
                    entry_points.extend(str(m.relative_to(workspace)) for m in matches[:3])
                else:
                    if (workspace / pattern).exists():
                        entry_points.append(pattern)
        
        return entry_points[:5]  # Limit to 5 entry points

    def _parse_metadata(self, workspace: Path, info: ProjectInfo) -> None:
        """Parse project metadata from config files."""
        # Python: pyproject.toml, setup.py, setup.cfg
        if info.project_type == 'python':
            pyproject = workspace / 'pyproject.toml'
            if pyproject.exists():
                try:
                    import tomli
                    with open(pyproject, 'rb') as f:
                        data = tomli.load(f)
                        if 'project' in data:
                            info.name = data['project'].get('name', info.name)
                            info.version = data['project'].get('version', '')
                            info.description = data['project'].get('description', '')
                except Exception:
                    pass
        
        # Node: package.json
        package_json = workspace / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    info.name = data.get('name', info.name)
                    info.version = data.get('version', '')
                    info.description = data.get('description', '')
            except Exception:
                pass
        
        # Rust: Cargo.toml
        cargo_toml = workspace / 'Cargo.toml'
        if cargo_toml.exists():
            try:
                import tomli
                with open(cargo_toml, 'rb') as f:
                    data = tomli.load(f)
                    if 'package' in data:
                        info.name = data['package'].get('name', info.name)
                        info.version = data['package'].get('version', '')
                        info.description = data['package'].get('description', '')
            except Exception:
                pass

    def _get_dependencies(self, workspace: Path, project_type: str) -> List[str]:
        """Get project dependencies."""
        deps = []
        
        if project_type == 'python':
            # requirements.txt
            req_file = workspace / 'requirements.txt'
            if req_file.exists():
                with open(req_file, 'r') as f:
                    deps = [line.split('==')[0].split('>=')[0].strip() 
                           for line in f if line.strip() and not line.startswith('#')]
            
            # pyproject.toml
            pyproject = workspace / 'pyproject.toml'
            if pyproject.exists():
                try:
                    import tomli
                    with open(pyproject, 'rb') as f:
                        data = tomli.load(f)
                        if 'project' in data and 'dependencies' in data['project']:
                            deps.extend(data['project']['dependencies'])
                except Exception:
                    pass
        
        elif project_type == 'node':
            package_json = workspace / 'package.json'
            if package_json.exists():
                try:
                    with open(package_json, 'r') as f:
                        data = json.load(f)
                        deps.extend(data.get('dependencies', {}).keys())
                        deps.extend(data.get('devDependencies', {}).keys())
                except Exception:
                    pass
        
        return deps[:20]  # Limit to 20 dependencies

    def _suggest_tools(self, workspace: Path, project_type: str) -> List[str]:
        """Suggest tools based on project type and what's missing."""
        suggested = []
        
        if project_type in self.RECOMMENDED_TOOLS:
            for tool in self.RECOMMENDED_TOOLS[project_type]:
                # Check if tool config exists (indicates tool is used)
                tool_configs = {
                    'prettier': ['.prettierrc', '.prettierrc.js', 'prettier.config.js'],
                    'eslint': ['.eslintrc', '.eslintrc.js', '.eslintrc.json'],
                    'ruff': ['ruff.toml', '.ruff.toml'],
                    'black': ['pyproject.toml'],  # Check if black section exists
                    'pytest': ['pytest.ini', 'pyproject.toml'],
                    'jest': ['jest.config.js', 'jest.config.ts'],
                }
                
                configs_exist = any((workspace / cfg).exists() for cfg in tool_configs.get(tool, []))
                
                if configs_exist or project_type in ['python', 'node']:
                    suggested.append(tool)
        
        return suggested

    def generate_skeleton(self, workspace: Path, max_depth: int = 2) -> Dict[str, Any]:
        """Generate a project skeleton with structure and metadata."""
        info = self.detect(workspace)
        
        skeleton = {
            'project': asdict(info),
            'structure': self._scan_structure(workspace, max_depth),
            'summary': self._generate_summary(info)
        }
        
        return skeleton

    def _scan_structure(self, workspace: Path, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Scan and return project structure."""
        structure = []
        excluded = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 
                   'dist', 'build', '.eggs', '*.egg-info', '.tox', '.pytest_cache'}
        
        def scan_dir(dir_path: Path, depth: int = 0, prefix: str = ''):
            if depth > max_depth:
                return
            
            try:
                items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                for item in items:
                    if item.name in excluded or item.name.startswith('.'):
                        continue
                    
                    rel_path = str(item.relative_to(workspace))
                    item_info = {
                        'name': item.name,
                        'path': rel_path,
                        'type': 'directory' if item.is_dir() else 'file',
                    }
                    
                    if item.is_file():
                        item_info['size'] = item.stat().st_size
                        item_info['extension'] = item.suffix
                    
                    structure.append(item_info)
                    
                    if item.is_dir():
                        scan_dir(item, depth + 1, prefix + '  ')
            except (PermissionError, OSError):
                pass
        
        scan_dir(workspace)
        return structure

    def _generate_summary(self, info: ProjectInfo) -> str:
        """Generate a human-readable project summary."""
        lines = [
            f"**Project:** {info.name}",
            f"**Type:** {info.project_type} (confidence: {info.confidence:.0%})",
        ]
        
        if info.version:
            lines.append(f"**Version:** {info.version}")
        
        if info.description:
            lines.append(f"**Description:** {info.description}")
        
        if info.languages:
            lines.append(f"**Languages:** {', '.join(sorted(info.languages))}")
        
        if info.frameworks:
            lines.append(f"**Frameworks:** {', '.join(sorted(info.frameworks))}")
        
        if info.entry_points:
            lines.append(f"**Entry Points:** {', '.join(info.entry_points)}")
        
        if info.key_files:
            lines.append(f"**Key Files:** {', '.join(info.key_files[:5])}")
        
        if info.tools_needed:
            lines.append(f"**Recommended Tools:** {', '.join(info.tools_needed)}")
        
        return '\n'.join(lines)


# Convenience function
def detect_project(workspace: Optional[Path] = None) -> ProjectInfo:
    """Detect project type for the given workspace."""
    if workspace is None:
        workspace = Path.cwd()
    
    detector = ProjectTypeDetector()
    return detector.detect(workspace)


def generate_skeleton(workspace: Optional[Path] = None) -> Dict[str, Any]:
    """Generate project skeleton for the given workspace."""
    if workspace is None:
        workspace = Path.cwd()
    
    detector = ProjectTypeDetector()
    return detector.generate_skeleton(workspace)
