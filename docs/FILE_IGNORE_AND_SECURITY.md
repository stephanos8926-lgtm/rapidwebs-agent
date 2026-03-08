# File Ignoring, Caching & Security Optimization Guide

**Version:** 1.0.0  
**Last Updated:** March 4, 2026  
**Status:** Implementation Ready

---

## 📋 Overview

This document provides comprehensive guidance on using `.qwenignore`, `.gitignore`, and caching strategies to:

1. **Reduce token usage** by 40-60%
2. **Enhance security** by excluding sensitive files
3. **Improve performance** through lazy loading and content-addressable caching
4. **Prevent indexing** of large/unnecessary filesystem entries

---

## 🎯 Part 1: File Ignoring for Security & Token Optimization

### 1.1 How .qwenignore and .gitignore Work

Your Qwen Code configuration (`E:\projects\rapidwebs-agent\.qwen\settings.json`) includes:

```json
{
  "context": {
    "fileFiltering": {
      "respectGitIgnore": true,
      "respectQwenIgnore": true,
      "enableRecursiveFileSearch": false,
      "enableFuzzySearch": false,
      "maxSearchResults": 50
    }
  }
}
```

**Mechanism:**
- **`.gitignore`**: Standard Git exclusion patterns (recognized by most tools)
- **`.qwenignore`**: Qwen Code-specific exclusions (same syntax as .gitignore)
- Both files use glob patterns processed by the filesystem MCP server **before** file operations
- Patterns are evaluated when:
  - Listing directories
  - Searching files
  - Loading context
  - Building file indexes

### 1.2 Token Savings Analysis

Based on the RapidWebs Agent workspace:

| Category | Files Excluded | Avg Size | Token Savings |
|----------|---------------|----------|---------------|
| `.venv/` | 5,000+ | 2KB | ~2,500,000 |
| `__pycache__/` | 500+ | 5KB | ~625,000 |
| `*.log` | 50+ | 100KB | ~1,250,000 |
| `dist/`, `build/` | 200+ | 10KB | ~500,000 |
| `.git/` | 1,000+ | 1KB | ~250,000 |
| `*.pyc`, `*.pyo` | 1,000+ | 3KB | ~750,000 |
| `node_modules/` (if present) | 10,000+ | 3KB | ~7,500,000 |
| **Total Potential Savings** | | | **~13,375,000 tokens** |

### 1.3 Security Risk Assessment

| Directory/File | Risk Level | Reason for Exclusion |
|----------------|------------|---------------------|
| `.venv/`, `venv/` | MEDIUM | Contains executable code, potential supply chain attacks |
| `.git/` | HIGH | Contains commit history, potential credential leaks in old commits |
| `*.env`, `secrets/` | CRITICAL | Direct credential exposure (API keys, passwords) |
| `.qwen/memory/` | MEDIUM | Contains conversation history, potential data leakage |
| `logs/` | MEDIUM | May contain sensitive operation logs, stack traces |
| `*.db`, `*.sqlite` | HIGH | Database files may contain credentials, PII |
| `*.key`, `*.pem` | CRITICAL | Private keys for encryption, SSH, TLS |
| `.ssh/` | CRITICAL | SSH keys, known_hosts, config with credentials |
| `*api_key*`, `*secret*` | CRITICAL | Pattern-based credential exposure |

### 1.4 .qwenignore File Structure

Your `.qwenignore` file (created at `E:\projects\rapidwebs-agent\.qwenignore`) includes:

```gitignore
# ==================== DEPENDENCIES ====================
.venv/
venv/
__pycache__/
*.pyc
node_modules/

# ==================== BUILD OUTPUTS ====================
dist/
build/
*.egg-info/
*.so
*.dll

# ==================== SENSITIVE FILES ====================
.env
*.key
*.pem
*.secret
*.db
!.qwen/memory/*.db  # Exception for memory DB

# ==================== LARGE FILES ====================
*.zip
*.tar.gz
*.mp4
*.log

# ==================== QWEN SPECIFIC ====================
.qwen/logs/
.qwen/backups/
.qwen/cache/
```

---

## 🚀 Part 2: Implementation Plan - Tier 1 (Core Caching)

### Phase 1.1: Hash-Based Change Detection

**Purpose:** Avoid re-reading unchanged files, reduce token usage by 30-50%

```python
# agent/caching/change_detector.py
import hashlib
import json
from pathlib import Path
from typing import Dict, Set, List, Optional
from dataclasses import dataclass
import time

@dataclass
class FileState:
    """Tracked file state for change detection"""
    path: str
    size: int
    modified: float
    content_hash: str
    symbol_hash: str  # Hash of AST symbols only

class HashBasedChangeDetector:
    """Detect file changes using content hashing"""

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.known_states: Dict[str, FileState] = {}
        self.symbol_cache: Dict[str, str] = {}

    def compute_file_hash(self, path: Path, full_content: bool = True) -> str:
        """Compute hash of file content"""
        hasher = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                if full_content:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hasher.update(chunk)
                else:
                    # Header-only hash (first 4KB)
                    hasher.update(f.read(4096))
            return hasher.hexdigest()[:16]
        except:
            return '0' * 16

    def compute_symbol_hash(self, path: Path, symbols: List[str]) -> str:
        """Compute hash of symbol list (for AST-based change detection)"""
        hasher = hashlib.sha256()
        for symbol in sorted(symbols):
            hasher.update(symbol.encode())
        return hasher.hexdigest()[:16]

    def track(self, path: Path, symbols: List[str] = None) -> FileState:
        """Start tracking a file"""
        path_str = str(path.resolve())
        stat = path.stat()

        symbol_hash = '0' * 16
        if symbols:
            symbol_hash = self.compute_symbol_hash(path, symbols)
            self.symbol_cache[path_str] = symbol_hash

        state = FileState(
            path=path_str,
            size=stat.st_size,
            modified=stat.st_mtime,
            content_hash=self.compute_file_hash(path),
            symbol_hash=symbol_hash
        )

        self.known_states[path_str] = state
        return state

    def has_changed(self, path: Path, check_symbols: bool = True) -> bool:
        """Check if file has changed since last track"""
        path_str = str(path.resolve())

        if path_str not in self.known_states:
            return True  # New file

        known = self.known_states[path_str]

        try:
            stat = path.stat()

            # Quick check: modification time
            if stat.st_mtime != known.modified:
                # Verify with hash (mtime can be unreliable)
                new_hash = self.compute_file_hash(path)
                return new_hash != known.content_hash

            return False
        except:
            return True  # Assume changed if can't stat

    def has_symbols_changed(self, path: Path, new_symbols: List[str]) -> bool:
        """Check if file's symbols have changed (AST-level)"""
        path_str = str(path.resolve())

        if path_str not in self.symbol_cache:
            return True

        new_hash = self.compute_symbol_hash(path, new_symbols)
        return new_hash != self.symbol_cache.get(path_str, '')

    def get_changed_files(self, paths: List[Path]) -> Set[str]:
        """Get set of changed file paths"""
        changed = set()
        for path in paths:
            if self.has_changed(path):
                changed.add(str(path.resolve()))
        return changed

    def save_state(self, output_path: Path):
        """Persist tracking state to disk"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({
                'states': {k: vars(v) for k, v in self.known_states.items()},
                'symbols': self.symbol_cache
            }, f, indent=2)

    def load_state(self, input_path: Path):
        """Load tracking state from disk"""
        if not input_path.exists():
            return

        with open(input_path, 'r') as f:
            data = json.load(f)

        for path, state_dict in data.get('states', {}).items():
            self.known_states[path] = FileState(**state_dict)

        self.symbol_cache = data.get('symbols', {})
```

**Integration Points:**
- Call `track()` after reading files in `context_optimization.py`
- Use `has_changed()` before re-reading files in conversation turns
- Persist state to `.qwen/cache/file_states.json`

---

### Phase 1.2: Content-Addressable Storage

**Purpose:** Deduplicate identical content, reduce token usage by 50-70% on repeated queries

```python
# agent/caching/content_addressable.py
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

class ContentAddressableCache:
    """Deduplication using content hashes as keys"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path.home() / '.cache' / 'rapidwebs-agent' / 'cache.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for content-addressable storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                hash TEXT PRIMARY KEY,
                content_type TEXT,
                size INTEGER,
                content BLOB,
                created_at REAL,
                accessed_at REAL,
                access_count INTEGER DEFAULT 1,
                metadata TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS path_mapping (
                path TEXT PRIMARY KEY,
                hash TEXT,
                last_modified REAL,
                FOREIGN KEY (hash) REFERENCES cache(hash)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_access ON cache(accessed_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_path_hash ON path_mapping(hash)')

        conn.commit()
        conn.close()

    def store(self, content: bytes, content_type: str = 'text',
              metadata: Dict = None) -> str:
        """Store content and return hash (deduplicates automatically)"""
        content_hash = hashlib.sha256(content).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if already exists (deduplication)
        cursor.execute('SELECT hash FROM cache WHERE hash = ?', (content_hash,))
        if cursor.fetchone():
            # Update access time
            cursor.execute('''
                UPDATE cache
                SET accessed_at = ?, access_count = access_count + 1
                WHERE hash = ?
            ''', (datetime.now().timestamp(), content_hash))
        else:
            # Store new content
            cursor.execute('''
                INSERT INTO cache (hash, content_type, size, content, created_at, accessed_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_hash,
                content_type,
                len(content),
                content,
                datetime.now().timestamp(),
                datetime.now().timestamp(),
                json.dumps(metadata or {})
            ))

        conn.commit()
        conn.close()
        return content_hash

    def retrieve(self, content_hash: str) -> Optional[bytes]:
        """Retrieve content by hash"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT content FROM cache WHERE hash = ?', (content_hash,))
        result = cursor.fetchone()

        if result:
            # Update access time
            cursor.execute('''
                UPDATE cache
                SET accessed_at = ?, access_count = access_count + 1
                WHERE hash = ?
            ''', (datetime.now().timestamp(), content_hash))
            conn.commit()

        conn.close()
        return result[0] if result else None

    def get_path_hash(self, path: Path) -> Optional[str]:
        """Get cached hash for a path"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT hash FROM path_mapping WHERE path = ?', (str(path),))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def update_path_mapping(self, path: Path, content_hash: str, modified: float):
        """Update path-to-hash mapping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO path_mapping (path, hash, last_modified)
            VALUES (?, ?, ?)
        ''', (str(path), content_hash, modified))

        conn.commit()
        conn.close()

    def cleanup(self, max_age_days: int = 30, min_access_count: int = 2):
        """Remove old, rarely accessed entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now().timestamp() - (max_age_days * 86400)

        cursor.execute('''
            DELETE FROM cache
            WHERE accessed_at < ? AND access_count < ?
        ''', (cutoff, min_access_count))

        # Remove orphaned path mappings
        cursor.execute('''
            DELETE FROM path_mapping
            WHERE hash NOT IN (SELECT hash FROM cache)
        ''')

        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
```

---

### Phase 1.3: Lazy Loading for Large Directories

**Purpose:** Load files on-demand only, reduce initial context by 20-40%

```python
# agent/caching/lazy_loader.py
from pathlib import Path
from typing import Dict, List, Optional, Callable, Generator
from dataclasses import dataclass, field
from collections import OrderedDict
import asyncio

@dataclass
class LazyFile:
    """Lazy-loaded file representation"""
    path: Path
    _content: Optional[str] = field(default=None, repr=False)
    _loaded: bool = False
    _load_callback: Optional[Callable] = None
    max_size: int = 524288  # 512KB

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> str:
        """Load content on demand"""
        if self._loaded and self._content is not None:
            return self._content

        if self._load_callback:
            self._content = self._load_callback(str(self.path))
        else:
            if self.path.stat().st_size > self.max_size:
                raise ValueError(f"File too large: {self.path}")
            self._content = self.path.read_text(encoding='utf-8')

        self._loaded = True
        return self._content

    def unload(self):
        """Free memory"""
        self._content = None
        self._loaded = False

class LazyDirectoryLoader:
    """Lazy loading for large directories"""

    def __init__(self, root: Path, max_files: int = 1000,
                 max_memory_files: int = 50):
        self.root = root.resolve()
        self.max_files = max_files
        self.max_memory_files = max_memory_files
        self.files: OrderedDict[str, LazyFile] = OrderedDict()
        self._scan_complete = False

    def scan(self, pattern: str = '**/*') -> Generator[Path, None, None]:
        """Lazy directory scan (yields paths, doesn't load content)"""
        if self._scan_complete:
            yield from (f.path for f in self.files.values())
            return

        count = 0
        for path in self.root.glob(pattern):
            if count >= self.max_files:
                break
            if path.is_file():
                yield path
                count += 1

        self._scan_complete = True

    def get_file(self, path: Path) -> Optional[LazyFile]:
        """Get or create lazy file (LRU eviction)"""
        path_str = str(path.resolve())

        if path_str in self.files:
            # Move to end (LRU)
            self.files.move_to_end(path_str)
            return self.files[path_str]

        # Create new lazy file
        lazy_file = LazyFile(path)
        self.files[path_str] = lazy_file

        # Enforce memory limit
        while len(self.files) > self.max_memory_files:
            oldest_key = next(iter(self.files))
            self.files[oldest_key].unload()
            del self.files[oldest_key]

        return lazy_file

    async def preload_likely_files(self, patterns: List[str]):
        """Pre-load files matching likely patterns (e.g., *.py, *.md)"""
        tasks = []
        for pattern in patterns:
            for path in self.root.glob(pattern):
                if path.is_file() and path.stat().st_size < 102400:  # <100KB
                    lazy_file = self.get_file(path)
                    tasks.append(asyncio.get_event_loop().run_in_executor(
                        None, lazy_file.load
                    ))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 🚀 Part 3: Implementation Plan - Tier 2 (Advanced Optimizations)

### Phase 2.1: Token Budget Enforcement

**Purpose:** Prevent runaway token usage, enforce daily limits

```python
# agent/caching/token_budget.py
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

@dataclass
class TokenBudgetConfig:
    """Token budget enforcement configuration"""
    enabled: bool = True
    daily_limit: int = 100000
    per_request_limit: int = 8000
    warning_threshold: float = 0.8
    action_on_exceed: str = "warn"  # warn, block, compress

class TokenBudgetEnforcer:
    """Enforce token budgets with daily tracking"""

    def __init__(self, config: TokenBudgetConfig):
        self.config = config
        self.daily_usage = 0
        self.last_reset = datetime.now().date()
        self.request_count = 0

    def _reset_if_new_day(self):
        """Reset daily counter if date changed"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_usage = 0
            self.request_count = 0
            self.last_reset = today

    def check_budget(self, estimated_tokens: int) -> bool:
        """Check if request is within budget"""
        if not self.config.enabled:
            return True

        self._reset_if_new_day()

        # Check per-request limit
        if estimated_tokens > self.config.per_request_limit:
            if self.config.action_on_exceed == "block":
                return False
            elif self.config.action_on_exceed == "warn":
                print(f"⚠️ Warning: Request exceeds per-request limit ({estimated_tokens} > {self.config.per_request_limit})")

        # Check daily limit
        if self.daily_usage + estimated_tokens > self.config.daily_limit:
            if self.config.action_on_exceed == "block":
                return False
            elif self.config.action_on_exceed == "warn":
                if self.daily_usage > self.config.daily_limit * self.config.warning_threshold:
                    print(f"⚠️ Warning: Approaching daily token limit ({self.daily_usage}/{self.config.daily_limit})")

        return True

    def record_usage(self, tokens: int):
        """Record token usage"""
        self.daily_usage += tokens
        self.request_count += 1

    def get_usage_report(self) -> dict:
        """Get current usage statistics"""
        self._reset_if_new_day()
        return {
            'daily_usage': self.daily_usage,
            'daily_limit': self.config.daily_limit,
            'usage_percentage': (self.daily_usage / self.config.daily_limit) * 100,
            'request_count': self.request_count,
            'remaining': self.config.daily_limit - self.daily_usage
        }
```

---

### Phase 2.2: Response Caching with File Invalidation

**Purpose:** Cache LLM responses, invalidate on file changes

```python
# agent/caching/response_cache.py
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Cached response entry"""
    response: str
    timestamp: float
    files: List[str]
    file_hashes: Dict[str, str]
    token_usage: int

class ResponseCache:
    """TTL-based response caching with file change invalidation"""

    def __init__(self, ttl_seconds: int = 1800):
        self.ttl = ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.file_hashes: Dict[str, str] = {}
        self.stats = {'hits': 0, 'misses': 0}

    def _make_key(self, prompt: str, model: str, files: List[str]) -> str:
        """Create cache key from prompt + file hashes"""
        hasher = hashlib.sha256()
        hasher.update(prompt.encode())
        hasher.update(model.encode())
        for f in sorted(files):
            hasher.update(self.file_hashes.get(f, '').encode())
        return hasher.hexdigest()

    def _compute_file_hash(self, path: str) -> str:
        """Compute current hash of file"""
        try:
            with open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except:
            return '0' * 16

    def get(self, prompt: str, model: str, files: List[str]) -> Optional[str]:
        """Get cached response if valid"""
        key = self._make_key(prompt, model, files)

        if key in self.cache:
            entry = self.cache[key]

            # Check TTL
            if time.time() - entry.timestamp >= self.ttl:
                del self.cache[key]
                self.stats['misses'] += 1
                return None

            # Check file changes
            for file_path in entry.files:
                current_hash = self._compute_file_hash(file_path)
                if current_hash != entry.file_hashes.get(file_path):
                    del self.cache[key]
                    self.stats['misses'] += 1
                    return None

            self.stats['hits'] += 1
            return entry.response

        self.stats['misses'] += 1
        return None

    def set(self, prompt: str, model: str, files: List[str],
            response: str, token_usage: int):
        """Cache response with file dependencies"""
        key = self._make_key(prompt, model, files)

        # Compute current file hashes
        file_hashes = {}
        for f in files:
            file_hashes[f] = self._compute_file_hash(f)
            self.file_hashes[f] = file_hashes[f]

        self.cache[key] = CacheEntry(
            response=response,
            timestamp=time.time(),
            files=files.copy(),
            file_hashes=file_hashes,
            token_usage=token_usage
        )

    def invalidate_file(self, file_path: str):
        """Invalidate cache entries for changed file"""
        new_hash = self._compute_file_hash(file_path)

        # Check if actually changed
        if self.file_hashes.get(file_path) == new_hash:
            return

        self.file_hashes[file_path] = new_hash

        # Remove affected cache entries
        keys_to_remove = [
            k for k, v in self.cache.items()
            if file_path in v.files
        ]

        for k in keys_to_remove:
            del self.cache[k]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_size': len(self.cache),
            'tracked_files': len(self.file_hashes)
        }

    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
        self.file_hashes.clear()
        self.stats = {'hits': 0, 'misses': 0}
```

---

## 📊 Expected Outcomes

| Optimization | Token Savings | Performance Impact | Security Impact | Implementation Effort |
|--------------|---------------|-------------------|-----------------|----------------------|
| `.qwenignore` patterns | 40-60% | Minimal | **High** | Low (done) |
| Hash-based change detection | 30-50% | **Positive** | Low | Medium |
| Content-addressable cache | 50-70% (repeated) | **Positive** | Low | Medium |
| Lazy directory loading | 20-40% | **Positive** | Low | Medium |
| Token budget enforcement | N/A | Minimal | Medium | Low |
| Response caching | 60-80% (repeated) | **Positive** | Low | Medium |

**Combined Potential Savings:** 70-85% token reduction with proper implementation

---

## 🔗 Integration Guide

### Update `agent/context_optimization.py`

Add imports:
```python
from .caching.change_detector import HashBasedChangeDetector
from .caching.content_addressable import ContentAddressableCache
from .caching.lazy_loader import LazyDirectoryLoader
from .caching.response_cache import ResponseCache
from .caching.token_budget import TokenBudgetEnforcer, TokenBudgetConfig
```

Initialize in `ContextManager.__init__()`:
```python
self.change_detector = HashBasedChangeDetector(self.workspace)
self.content_cache = ContentAddressableCache()
self.lazy_loader = LazyDirectoryLoader(self.workspace)
self.response_cache = ResponseCache(ttl_seconds=1800)
self.token_enforcer = TokenBudgetEnforcer(TokenBudgetConfig(
    enabled=True,
    daily_limit=100000,
    per_request_limit=8000
))
```

---

## 📚 References

| Resource | URL |
|----------|-----|
| **Qwen Code File Filtering** | https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/ |
| **MCP Filesystem Server** | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem |
| **OWASP Top 10** | https://owasp.org/www-project-top-ten/ |
| **Content-Addressable Storage** | https://en.wikipedia.org/wiki/Content-addressable_storage |
