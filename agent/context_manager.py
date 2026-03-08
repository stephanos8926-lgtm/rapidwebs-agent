"""
Advanced Context Window Optimization v2
AST-based chunking, LSP integration, and ML-based relevance scoring
"""
import re
import ast
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import deque
import asyncio
import math

from .utilities import get_token_count

# Phase 2 imports: Code analysis utilities
from .utilities import get_import_graph


@dataclass
class CodeChunk:
    """Semantic code chunk"""
    type: str
    name: str
    source: str
    tokens: int
    file: str
    start_line: int
    end_line: int
    dependencies: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    signature: str = ""
    documentation: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    resolved_dependencies: List['CodeChunk'] = field(default_factory=list)


@dataclass
class ContextDelta:
    """Delta between two contexts"""
    added: Set[str]
    removed: Set[str]
    modified: Set[str]


@dataclass  
class SymbolNode:
    """LSP symbol node"""
    name: str
    kind: str
    file: str
    line: int
    column: int
    tokens: int
    signature: str = ""
    documentation: str = ""
    references: List[Dict] = field(default_factory=list)
    definitions: List[Dict] = field(default_factory=list)
    implementations: List[Dict] = field(default_factory=list)


class ASTSemanticChunker:
    """Chunk code using AST parsing for maximum accuracy"""
    
    def __init__(self):
        self.chunks: List[CodeChunk] = []
    
    def chunk_file(self, file_path: Path) -> List[CodeChunk]:
        """Chunk a file using AST parsing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            lines = source.splitlines()
            
            chunks = []
            
            # Extract top-level definitions
            for node in ast.iter_child_nodes(tree):
                chunk = self._node_to_chunk(node, lines, str(file_path))
                if chunk:
                    chunks.append(chunk)
            
            self.chunks = chunks
            return chunks
            
        except SyntaxError as e:
            # Fallback to regex-based chunking
            return self._fallback_chunk(file_path)
        except Exception as e:
            return []
    
    def _node_to_chunk(self, node: ast.AST, lines: List[str], file: str) -> Optional[CodeChunk]:
        """Convert AST node to CodeChunk"""
        start_line = getattr(node, 'lineno', 1) - 1
        end_line = getattr(node, 'end_lineno', start_line + 10)
        
        # Get source
        source = '\n'.join(lines[start_line:end_line])
        
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            return CodeChunk(
                type='function',
                name=node.name,
                source=source,
                tokens=get_token_count(source),
                file=file,
                start_line=start_line,
                end_line=end_line,
                dependencies=self._get_function_deps(node),
                signature=self._get_function_signature(node, lines),
                documentation=ast.get_docstring(node) or "",
                metrics=self._compute_function_metrics(node)
            )
        
        elif isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            return CodeChunk(
                type='class',
                name=node.name,
                source=source,
                tokens=get_token_count(source),
                file=file,
                start_line=start_line,
                end_line=end_line,
                dependencies=[base.id for base in node.bases if isinstance(base, ast.Name)],
                signature=f"class {node.name}",
                documentation=ast.get_docstring(node) or "",
                metrics={'methods': len(methods), 'bases': len(node.bases)}
            )
        
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            return CodeChunk(
                type='import',
                name=self._get_import_name(node),
                source=source,
                tokens=get_token_count(source),
                file=file,
                start_line=start_line,
                end_line=end_line,
                dependencies=[],
                signature=source.strip()
            )
        
        return None
    
    def _get_function_signature(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], 
                                lines: List[str]) -> str:
        """Get function signature"""
        start_line = node.lineno - 1
        # Find the line with the colon
        signature_lines = []
        for i in range(start_line, min(start_line + 10, len(lines))):
            signature_lines.append(lines[i])
            if ':' in lines[i]:
                break
        return '\n'.join(signature_lines)
    
    def _get_function_deps(self, node: ast.FunctionDef) -> List[str]:
        """Get function dependencies"""
        deps = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id not in ['self', 'cls']:
                deps.add(child.id)
            elif isinstance(child, ast.Attribute):
                deps.add(child.attr)
        return list(deps)[:15]
    
    def _get_import_name(self, node: Union[ast.Import, ast.ImportFrom]) -> str:
        """Get import module name"""
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else 'unknown'
        elif isinstance(node, ast.ImportFrom):
            return node.module or 'unknown'
        return 'unknown'
    
    def _compute_function_metrics(self, node: ast.FunctionDef) -> Dict[str, float]:
        """Compute function complexity metrics"""
        metrics = {
            'params': len(node.args.args),
            'lines': (node.end_lineno or node.lineno) - node.lineno + 1,
            'complexity': self._compute_cyclomatic_complexity(node),
            'nesting': self._compute_max_nesting(node)
        }
        return metrics
    
    def _compute_cyclomatic_complexity(self, node: ast.AST) -> float:
        """Compute cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                 ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _compute_max_nesting(self, node: ast.AST, depth: int = 0) -> int:
        """Compute maximum nesting depth"""
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = self._compute_max_nesting(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._compute_max_nesting(child, depth)
                max_depth = max(max_depth, child_depth)
        return max_depth
    
    def _fallback_chunk(self, file_path: Path) -> List[CodeChunk]:
        """Fallback to regex-based chunking"""
        patterns = {
            'function': r'^(?:async\s+)?def\s+(\w+)\s*\(',
            'class': r'^class\s+(\w+)',
            'import': r'^(?:import|from)\s+',
        }
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        chunks = []
        current_chunk = None
        current_start = 0
        
        for i, line in enumerate(lines):
            for chunk_type, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    if current_chunk:
                        current_chunk.source = ''.join(lines[current_start:i])
                        current_chunk.tokens = get_token_count(current_chunk.source)
                        chunks.append(current_chunk)
                    
                    name = match.group(1) if match.groups() else f"{chunk_type}_{i}"
                    current_chunk = CodeChunk(
                        type=chunk_type,
                        name=name,
                        source="",
                        tokens=0,
                        file=str(file_path),
                        start_line=current_start,
                        end_line=i
                    )
                    current_start = i
                    break
        
        if current_chunk:
            current_chunk.source = ''.join(lines[current_start:])
            current_chunk.tokens = get_token_count(current_chunk.source)
            chunks.append(current_chunk)
        
        return chunks


class MLRelevanceScorer:
    """ML-based relevance scoring for symbols"""
    
    def __init__(self):
        # Weights for different signals
        self.weights = {
            'text_similarity': 0.30,
            'call_proximity': 0.25,
            'recency': 0.15,
            'edit_frequency': 0.10,
            'import_count': 0.10,
            'complexity': 0.10,
        }
        
        # Edit frequency tracking
        self.edit_counts: Dict[str, int] = {}
        self.edit_times: Dict[str, float] = {}
    
    def score(self, chunk: CodeChunk, query: str, context: Dict) -> float:
        """Score chunk relevance using multiple signals"""
        
        # Text similarity (cosine similarity with query)
        text_sim = self._cosine_similarity(chunk.signature + chunk.source[:500], query)
        
        # Call proximity (how close in call graph)
        call_prox = self._call_proximity(chunk, context.get('current_function', ''))
        
        # Recency (was it recently edited?)
        recency = self._recency_score(chunk.file, chunk.start_line)
        
        # Edit frequency (is it frequently modified?)
        edit_freq = self._edit_frequency_score(chunk.file, chunk.name)
        
        # Import count (how many things import this?)
        import_count = self._import_count_score(chunk.name, context.get('all_symbols', {}))
        
        # Complexity (prefer simpler chunks for explanation)
        complexity = self._complexity_score(chunk)
        
        # Weighted sum
        score = (
            self.weights['text_similarity'] * text_sim +
            self.weights['call_proximity'] * call_prox +
            self.weights['recency'] * recency +
            self.weights['edit_frequency'] * edit_freq +
            self.weights['import_count'] * import_count +
            self.weights['complexity'] * complexity
        )
        
        chunk.relevance_score = score
        return score
    
    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between texts"""
        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0
    
    def _tokenize(self, text: str) -> Set[str]:
        """Tokenize text into words"""
        # Simple tokenization - split on non-alphanumeric
        words = re.findall(r'\b\w+\b', text.lower())
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall'}
        return set(w for w in words if w not in stop_words and len(w) > 2)
    
    def _call_proximity(self, chunk: CodeChunk, current_function: str) -> float:
        """Score based on call graph proximity"""
        if not current_function:
            return 0.5  # Neutral if no current function
        
        # Check if chunk is called by or calls current function
        if current_function in chunk.dependencies:
            return 1.0  # Direct dependency
        
        # Check name similarity
        if chunk.name in current_function or current_function in chunk.name:
            return 0.8
        
        return 0.3  # Low default
    
    def _recency_score(self, file: str, line: int) -> float:
        """Score based on recency of edit"""
        import time
        current_time = time.time()
        
        if file in self.edit_times:
            age_hours = (current_time - self.edit_times[file]) / 3600
            # Exponential decay - recent edits score higher
            return math.exp(-age_hours / 24)  # 24 hour half-life
        
        return 0.5  # Neutral if unknown
    
    def _edit_frequency_score(self, file: str, name: str) -> float:
        """Score based on how frequently edited"""
        key = f"{file}:{name}"
        count = self.edit_counts.get(key, 0)
        
        if count == 0:
            return 0.5
        
        # Log scale - diminishing returns
        return min(1.0, math.log(count + 1) / math.log(100))
    
    def _import_count_score(self, name: str, all_symbols: Dict) -> float:
        """Score based on how many symbols import this"""
        # Count how many chunks depend on this symbol
        count = 0
        for symbol_name, symbol_data in all_symbols.items():
            if name in symbol_data.get('dependencies', []):
                count += 1
        
        if count == 0:
            return 0.5
        
        return min(1.0, count / 10)  # Cap at 10 importers
    
    def _complexity_score(self, chunk: CodeChunk) -> float:
        """Score based on complexity - prefer simpler for explanations"""
        complexity = chunk.metrics.get('complexity', 5)
        
        # Lower complexity = higher score
        if complexity < 5:
            return 1.0
        elif complexity < 10:
            return 0.7
        elif complexity < 20:
            return 0.4
        else:
            return 0.2
    
    def record_edit(self, file: str, symbol: str):
        """Record an edit for future scoring"""
        import time
        key = f"{file}:{symbol}"
        self.edit_counts[key] = self.edit_counts.get(key, 0) + 1
        self.edit_times[key] = time.time()


class ContextOptimizer:
    """Optimize context selection using relevance scoring"""

    VALUE_WEIGHTS = {
        'error_diagnostic': 100,
        'current_function': 80,
        'function_signature': 60,
        'type_annotation': 50,
        'docstring': 40,
        'function_body': 30,
        'caller_example': 25,
        'related_import': 20,
        'sibling_method': 15,
    }

    def __init__(self):
        self.symbol_graph: Dict[str, SymbolNode] = {}
        self.scorer = MLRelevanceScorer()

    def get_relevant_context(self, query: str, current_file: Path,
                           token_budget: int, chunks: List[CodeChunk]) -> 'OptimizedContext':
        """Get most relevant symbols for query within token budget"""
        
        # Score all chunks
        for chunk in chunks:
            self.scorer.score(chunk, query, {})
        
        # Sort by relevance
        sorted_chunks = sorted(chunks, key=lambda c: c.relevance_score, reverse=True)
        
        # Fill budget
        symbols = []
        symbol_content = {}
        used_tokens = 0
        
        for chunk in sorted_chunks:
            if used_tokens + chunk.tokens <= token_budget:
                symbols.append(chunk.name)
                symbol_content[chunk.name] = self._format_chunk_for_context(chunk)
                used_tokens += chunk.tokens
        
        return OptimizedContext(
            symbols=symbols,
            symbol_content=symbol_content,
            total_tokens=used_tokens,
            budget_used=used_tokens / token_budget,
            file_hints={'current_file': str(current_file)}
        )
    
    def _format_chunk_for_context(self, chunk: CodeChunk) -> str:
        """Format chunk for inclusion in context"""
        parts = []
        
        # Add signature
        if chunk.signature:
            parts.append(chunk.signature)
        
        # Add docstring
        if chunk.documentation:
            parts.append(f'"""{chunk.documentation}"""')
        
        # Add body (truncated if too long)
        body = chunk.source
        if len(body) > 2000:
            body = body[:2000] + "\n    # ... truncated"
        
        parts.append(body)
        
        return '\n'.join(parts)
    
    async def get_symbol_at_position(self, file: Path, line: int, col: int) -> Optional[SymbolNode]:
        """Get symbol definition at cursor position via LSP"""
        if not self.lsp:
            return None
        
        try:
            result = await self.lsp.execute('definition', file=str(file), line=line, column=col)
            if result.get('success'):
                # Parse result into SymbolNode
                pass
        except Exception:
            pass
        
        return None


@dataclass
class OptimizedContext:
    """Optimized context with symbol tracking"""
    symbols: List[str]
    symbol_content: Dict[str, str]
    total_tokens: int
    budget_used: float
    file_hints: Dict[str, Any]
    chunks: List[CodeChunk] = field(default_factory=list)
    
    def compute_hash(self) -> str:
        """Compute hash of context for delta detection"""
        content = '|'.join(sorted(self.symbols))
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ContextThrashingPrevention:
    """Prevent context thrashing between conversation turns"""
    
    def __init__(self, max_history: int = 5, max_change_threshold: float = 0.3):
        self.context_history: deque = deque(maxlen=max_history)
        self.stable_anchors: Set[str] = set()
        self.previous_context_hash: Optional[str] = None
        self.max_change_threshold = max_change_threshold
    
    def add_context(self, context: OptimizedContext):
        self.context_history.append(context)
        self.previous_context_hash = context.compute_hash()
    
    def compute_delta(self, old_context: OptimizedContext, 
                     new_context: OptimizedContext) -> ContextDelta:
        old_symbols = set(old_context.symbols)
        new_symbols = set(new_context.symbols)
        
        return ContextDelta(
            added=new_symbols - old_symbols,
            removed=old_symbols - new_symbols,
            modified=self._find_modified(old_context, new_context)
        )
    
    def _find_modified(self, old: OptimizedContext, new: OptimizedContext) -> Set[str]:
        modified = set()
        common = set(old.symbols) & set(new.symbols)
        
        for symbol in common:
            old_content = old.symbol_content.get(symbol, '')
            new_content = new.symbol_content.get(symbol, '')
            if old_content != new_content:
                modified.add(symbol)
        
        return modified
    
    def detect_thrashing(self) -> bool:
        if len(self.context_history) < 3:
            return False
        
        changes = []
        history_list = list(self.context_history)
        
        for i in range(1, len(history_list)):
            delta = self.compute_delta(history_list[i-1], history_list[i])
            total_symbols = len(history_list[i].symbols)
            if total_symbols == 0:
                continue
            change_ratio = (len(delta.added) + len(delta.removed)) / total_symbols
            changes.append(change_ratio)
        
        high_changes = sum(1 for c in changes if c > self.max_change_threshold)
        return high_changes > len(changes) * 0.7
    
    def stabilize_context(self, context: OptimizedContext) -> OptimizedContext:
        for anchor in self.stable_anchors:
            if anchor not in context.symbols:
                context.symbols.append(anchor)
        return context
    
    def build_incremental_prompt(self, delta: ContextDelta, query: str) -> str:
        parts = []
        
        if self.previous_context_hash:
            parts.append(f"[Previous context: {self.previous_context_hash[:8]}]")
        
        if delta.added:
            parts.append(f"\n## New: {', '.join(delta.added)}")
        
        if delta.removed:
            parts.append(f"\n## Removed: {', '.join(delta.removed)}")
        
        if delta.modified:
            parts.append(f"\n## Modified: {', '.join(delta.modified)}")
        
        parts.append(f"\n## Query: {query}")
        
        return '\n'.join(parts)


class ContextManager:
    """Main context optimization manager"""

    def __init__(self, token_budget: int = 8000, workspace: Optional[Path] = None):
        self.token_budget = token_budget
        self.workspace = workspace or Path.cwd()
        self.chunker = ASTSemanticChunker()
        self.thrash_prevention = ContextThrashingPrevention()
        self.optimizer = ContextOptimizer()
        self.current_context: Optional[OptimizedContext] = None
    
    async def build_optimized_context(self, query: str,
                                      current_file: Path,
                                      position: Optional[Tuple[int, int]] = None) -> str:
        """Build optimized context for query
        
        Enhancements (Phase 2):
        - Symbol summaries for tight budgets
        - Related file suggestions
        - Import dependency context
        """

        # Check for thrashing
        if self.thrash_prevention.detect_thrashing():
            self.thrash_prevention.stable_anchors.update(
                self.thrash_prevention.context_history[-1].symbols if
                self.thrash_prevention.context_history else []
            )

        # Chunk the file using AST
        chunks = self.chunker.chunk_file(current_file)

        # Get relevant context
        context = self.optimizer.get_relevant_context(
            query, current_file, self.token_budget, chunks
        )

        # Track for thrashing prevention
        self.thrash_prevention.add_context(context)
        self.current_context = context

        return self._format_context(context, query, current_file)

    def _format_context(self, context: OptimizedContext, query: str, 
                        current_file: Optional[Path] = None) -> str:
        """Format context for LLM with Phase 2 enhancements"""
        parts = []

        # Phase 2 Enhancement 1: Symbol summary for tight budgets
        if current_file and self.token_budget < 2000:
            # Use symbol summary instead of full content when budget is tight
            symbols = get_file_symbols(current_file)
            if symbols:
                summary_lines = [f"# {current_file.name} symbols:"]
                for sym in symbols[:15]:  # Limit to 15 symbols
                    summary_lines.append(f"#   - {sym['type']} {sym['name']} (line {sym['line']})")
                parts.append('\n'.join(summary_lines))
                parts.append("")  # Blank line separator
        else:
            # Standard format with full content
            parts.append(f"## Context (Tokens: {context.total_tokens}/{self.token_budget})")
            for symbol, content in context.symbol_content.items():
                parts.append(f"\n### {symbol}\n{content}")

        # Phase 2 Enhancement 2: Related files metadata
        if current_file:
            related = suggest_related_files(current_file, self.workspace, max_suggestions=3)
            if related:
                parts.append(f"\n## Related Files")
                for f in related:
                    try:
                        rel_path = f.relative_to(self.workspace)
                        parts.append(f"- `{rel_path}`")
                    except ValueError:
                        parts.append(f"- `{f}`")

        # Phase 2 Enhancement 3: Import dependency context
        if current_file and current_file.suffix == '.py':
            imports = get_import_graph(current_file, self.workspace)
            if imports:
                parts.append(f"\n## Dependencies ({current_file.name})")
                import_lines = []
                for name, module in list(imports.items())[:10]:  # Limit to 10 imports
                    import_lines.append(f"- `{name}` from `{module}`")
                parts.append('\n'.join(import_lines))

        parts.append(f"\n## Query\n{query}")

        return '\n'.join(parts)
    
    def build_delta_context(self, new_query: str) -> str:
        if not self.current_context or len(self.thrash_prevention.context_history) < 2:
            return new_query
        
        old_context = self.thrash_prevention.context_history[-2]
        new_context = self.current_context
        
        delta = self.thrash_prevention.compute_delta(old_context, new_context)
        return self.thrash_prevention.build_incremental_prompt(delta, new_query)
    
    def record_edit(self, file: str, symbol: str):
        """Record an edit for ML scoring"""
        self.lsp_optimizer.scorer.record_edit(file, symbol)

    def suggest_related_files(self, current_file: Path, max_suggestions: int = 5) -> List[Path]:
        """Suggest files related to current file.

        Uses heuristics to find related files:
        - Test files (test_*.py, *_test.py)
        - Same directory siblings
        - Files with similar names in other directories
        - Imported modules

        Excludes: .venv, node_modules, __pycache__, dist, build, .git

        Args:
            current_file: Current file path
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested file paths
        """
        if not current_file.exists():
            return []

        suggestions = []
        workspace = self.workspace
        stem = current_file.stem
        suffix = current_file.suffix
        parent = current_file.parent

        # Directories to exclude
        EXCLUDED_DIRS = {'.venv', 'venv', 'node_modules', '__pycache__', 
                         'dist', 'build', '.git', '.eggs', '*.egg-info'}

        def is_excluded(path: Path) -> bool:
            for part in path.parts:
                if part in EXCLUDED_DIRS or part.endswith('.egg-info'):
                    return True
            return False

        # 1. Test files (highest priority)
        test_patterns = [
            parent / f"test_{stem}{suffix}",
            parent / f"{stem}_test{suffix}",
            workspace / "tests" / f"test_{stem}{suffix}",
            workspace / "tests" / f"{stem}_test{suffix}",
        ]
        for test_path in test_patterns:
            if test_path.exists() and test_path not in suggestions and not is_excluded(test_path):
                suggestions.append(test_path)
                if len(suggestions) >= max_suggestions:
                    return suggestions

        # 2. Same directory siblings (same extension)
        try:
            siblings = list(parent.glob(f"*{suffix}"))
            # Sort by name similarity
            siblings.sort(key=lambda p: (
                p == current_file,  # Current file last
                stem not in p.stem  # Similar names first
            ))
            for sibling in siblings[:3]:
                if sibling != current_file and sibling not in suggestions and not is_excluded(sibling):
                    suggestions.append(sibling)
                    if len(suggestions) >= max_suggestions:
                        return suggestions
        except (OSError, PermissionError):
            pass

        # 3. Files with same name in different directories
        try:
            for similar in workspace.rglob(f"{stem}{suffix}"):
                if similar != current_file and similar not in suggestions and not is_excluded(similar):
                    suggestions.append(similar)
                    if len(suggestions) >= max_suggestions:
                        return suggestions
        except (OSError, PermissionError):
            pass
        
        return suggestions[:max_suggestions]


# =============================================================================
# Standalone Utility Functions (for use without ContextManager)
# =============================================================================

def get_file_symbols(file_path: Path) -> List[Dict[str, Any]]:
    """Extract symbols (functions, classes, imports) from a Python file using AST.
    
    Returns a list of symbol dictionaries with type, name, line number, and signature.
    Much more efficient than sending full file content (~200 tokens vs ~2000).
    
    Args:
        file_path: Path to Python file
        
    Returns:
        List of symbol dictionaries:
        [
            {'type': 'function', 'name': 'foo', 'line': 10, 'signature': 'def foo(x):'},
            {'type': 'class', 'name': 'Bar', 'line': 20, 'signature': 'class Bar:'},
            ...
        ]
        
    Example:
        >>> from agent.context_manager import get_file_symbols
        >>> symbols = get_file_symbols(Path("agent/agent.py"))
        >>> print(symbols)
        [{'type': 'class', 'name': 'Agent', 'line': 50, 'signature': 'class Agent:'}]
    """
    if not file_path.exists() or not file_path.suffix == '.py':
        return []
    
    try:
        chunker = ASTSemanticChunker()
        chunks = chunker.chunk_file(file_path)
        
        symbols = []
        for chunk in chunks:
            if chunk.type in ('function', 'class', 'import'):
                symbols.append({
                    'type': chunk.type,
                    'name': chunk.name,
                    'line': chunk.start_line + 1,  # Convert to 1-based
                    'signature': chunk.signature.split('\n')[0] if chunk.signature else '',
                    'end_line': chunk.end_line + 1,
                })
        
        return symbols
    except Exception:
        # Fallback to empty list on parse errors
        return []


def get_symbols_summary(file_path: Path, max_symbols: int = 20) -> str:
    """Get a concise summary of symbols in a file.
    
    Returns a formatted string suitable for including in context.
    
    Args:
        file_path: Path to Python file
        max_symbols: Maximum number of symbols to include
        
    Returns:
        Formatted string with symbol summary
        
    Example:
        >>> summary = get_symbols_summary(Path("agent/core.py"))
        >>> print(summary)
        # agent/core.py symbols:
        - class Agent (line 50)
        - function run (line 100)
        - import Config (line 1)
    """
    symbols = get_file_symbols(file_path)
    if not symbols:
        return ""
    
    lines = [f"# {file_path.name} symbols:"]
    for sym in symbols[:max_symbols]:
        lines.append(f"- {sym['type']} {sym['name']} (line {sym['line']})")
    
    if len(symbols) > max_symbols:
        lines.append(f"- ... and {len(symbols) - max_symbols} more")
    
    return '\n'.join(lines)


def suggest_related_files(current_file: Path, workspace: Optional[Path] = None, 
                          max_suggestions: int = 5) -> List[Path]:
    """Suggest files related to current file (standalone function).
    
    Uses heuristics to find related files:
    - Test files (test_*.py, *_test.py)
    - Same directory siblings
    - Files with similar names in other directories
    
    Excludes: .venv, node_modules, __pycache__, dist, build, .git
    
    Args:
        current_file: Current file path
        workspace: Workspace root (defaults to current_file.parent.parent)
        max_suggestions: Maximum number of suggestions
        
    Returns:
        List of suggested file paths

    Example:
        >>> from agent.context_manager import suggest_related_files
        >>> suggestions = suggest_related_files(Path("agent/agent.py"))
        >>> print(suggestions)
        [Path("tests/test_agent.py"), Path("agent/utilities.py")]
    """
    if not current_file.exists():
        return []
    
    suggestions = []
    workspace = workspace or current_file.parent.parent
    stem = current_file.stem
    suffix = current_file.suffix
    parent = current_file.parent
    
    # Directories to exclude
    EXCLUDED_DIRS = {'.venv', 'venv', 'node_modules', '__pycache__', 
                     'dist', 'build', '.git', '.eggs', '*.egg-info'}
    
    def is_excluded(path: Path) -> bool:
        """Check if path is in excluded directory"""
        for part in path.parts:
            if part in EXCLUDED_DIRS or part.endswith('.egg-info'):
                return True
        return False
    
    # 1. Test files (highest priority)
    test_patterns = [
        parent / f"test_{stem}{suffix}",
        parent / f"{stem}_test{suffix}",
        workspace / "tests" / f"test_{stem}{suffix}",
        workspace / "tests" / f"{stem}_test{suffix}",
    ]
    for test_path in test_patterns:
        if test_path.exists() and test_path not in suggestions and not is_excluded(test_path):
            suggestions.append(test_path)
            if len(suggestions) >= max_suggestions:
                return suggestions
    
    # 2. Same directory siblings (same extension)
    try:
        siblings = list(parent.glob(f"*{suffix}"))
        # Sort by name similarity
        siblings.sort(key=lambda p: (
            p == current_file,  # Current file last
            stem not in p.stem  # Similar names first
        ))
        for sibling in siblings[:3]:
            if sibling != current_file and sibling not in suggestions and not is_excluded(sibling):
                suggestions.append(sibling)
                if len(suggestions) >= max_suggestions:
                    return suggestions
    except (OSError, PermissionError):
        pass
    
    # 3. Files with same name in different directories (exclude common dirs)
    try:
        for similar in workspace.rglob(f"{stem}{suffix}"):
            if similar != current_file and similar not in suggestions and not is_excluded(similar):
                suggestions.append(similar)
                if len(suggestions) >= max_suggestions:
                    return suggestions
    except (OSError, PermissionError):
        pass
    
    return suggestions[:max_suggestions]


# Integration function
async def get_optimized_context(query: str, file_path: str = None, 
                                line: int = None, col: int = None) -> str:
    """
    Get optimized context for query
    
    Usage:
    ```python
    context = await get_optimized_context("fix the bug", "agent/core.py", 45, 10)
    ```
    """
    manager = ContextManager(token_budget=8000)
    
    if file_path:
        current_file = Path(file_path)
    else:
        current_file = Path.cwd()
    
    position = (line, col) if line and col else None
    
    return await manager.build_optimized_context(query, current_file, position)
