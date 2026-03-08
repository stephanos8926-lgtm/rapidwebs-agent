# -*- coding: utf-8 -*-
"""
Unified Prompt Optimizer for Qwen Code CLI
==========================================
Combines memory optimization (A-MAC scoring) and prompt compression.

Three modes (controlled by config/env var):
1. REPORT: Generate optimization report only (no changes)
2. OPTIMIZE: Apply optimizations and update original files
3. SAVE: Save optimized versions to dedicated folder (preserve originals)

Configuration via:
- Environment variable: QWEN_OPT_MODE=report|optimize|save
- Config file: .qwen/optimizer-config.json
- Command line: --mode report|optimize|save

Author: RapidWebs Agent
Version: 2.0.0
Date: 2026-03-08
"""

import re
import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class OptimizerConfig:
    """Configuration for prompt optimization."""
    mode: str = 'report'  # report, optimize, save
    min_memory_score: float = 5.5
    compression_level: str = 'standard'  # light, standard, aggressive
    create_backups: bool = True
    optimized_folder: str = 'optimized-prompts'
    log_file: Optional[str] = None
    verbose: bool = True
    
    @classmethod
    def load(cls) -> 'OptimizerConfig':
        """Load configuration from env vars and config file."""
        config = cls()
        
        # Load from config file
        config_paths = [
            Path('.qwen/optimizer-config.json'),
            Path('hooks/optimizer-config.json'),
            Path.home() / '.qwen' / 'optimizer-config.json',
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    file_config = json.loads(config_path.read_text(encoding='utf-8'))
                    for key, value in file_config.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                    break
                except (json.JSONDecodeError, IOError):
                    pass
        
        # Override with environment variables
        env_mode = os.environ.get('QWEN_OPT_MODE', '').lower()
        if env_mode in ['report', 'optimize', 'save']:
            config.mode = env_mode
        
        env_score = os.environ.get('QWEN_MIN_SCORE', '')
        if env_score:
            try:
                config.min_memory_score = float(env_score)
            except ValueError:
                pass
        
        env_verbose = os.environ.get('QWEN_OPT_VERBOSE', '')
        if env_verbose.lower() in ['1', 'true', 'yes']:
            config.verbose = True
        elif env_verbose.lower() in ['0', 'false', 'no']:
            config.verbose = False
        
        return config
    
    def save(self, path: str = '.qwen/optimizer-config.json'):
        """Save configuration to file."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(asdict(self), indent=2),
            encoding='utf-8'
        )


# ============================================================================
# MEMORY OPTIMIZATION (A-MAC Algorithm)
# ============================================================================

class MemoryScorer:
    """A-MAC based memory scoring."""
    
    WEIGHTS = {
        'utility': 0.35,
        'novelty': 0.25,
        'recency': 0.15,
        'specificity': 0.15,
        'position': 0.10,
    }
    
    CATEGORY_BOOSTS = {
        'architecture_decision': 1.2,
        'error_prevention': 1.15,
        'user_preference': 1.1,
        'implementation_detail': 1.1,
        'project_context': 1.05,
        'tool_configuration': 1.0,
        'session_summary': 0.9,
        'debug_context': 0.85,
        'raw_tool_output': 0.7,
        'conversational filler': 0.6,
    }
    
    def score_memories(self, memories: List[Dict]) -> List[Dict]:
        """Score memories and return scored list."""
        scored = []
        
        for i, memory in enumerate(memories):
            content = memory.get('content', '')
            category = memory.get('category', 'general')
            
            # Calculate scores
            utility = self._calc_utility(content, category)
            novelty = self._calc_novelty(content, memories[:i])
            recency = 5.0  # Default (no timestamp info)
            specificity = self._calc_specificity(content)
            position = self._calc_position(i, len(memories))
            
            # Apply category boost
            boost = self.CATEGORY_BOOSTS.get(category, 1.0)
            
            # Composite score
            composite = (
                utility * self.WEIGHTS['utility'] +
                novelty * self.WEIGHTS['novelty'] +
                recency * self.WEIGHTS['recency'] +
                specificity * self.WEIGHTS['specificity'] +
                position * self.WEIGHTS['position']
            ) * boost
            
            # Decision
            if composite >= 7.0:
                decision = 'AUTO-ADMIT'
            elif composite >= 5.5:
                decision = 'REVIEW'
            else:
                decision = 'SUMMARIZE'
            
            scored.append({
                'content': content,
                'category': category,
                'utility': round(utility, 2),
                'novelty': round(novelty, 2),
                'specificity': round(specificity, 2),
                'composite': round(composite, 2),
                'decision': decision,
            })
        
        return scored
    
    def _calc_utility(self, content: str, category: str) -> float:
        """Calculate utility score (0-10)."""
        score = 5.0
        content_lower = content.lower()
        
        # High utility patterns
        if any(w in content_lower for w in ['must', 'critical', 'always', 'never']):
            score += 2.0
        if any(w in content_lower for w in ['architecture', 'design', 'pattern']):
            score += 2.0
        if any(w in content_lower for w in ['error', 'prevent', 'avoid', 'bug']):
            score += 1.5
        if any(w in content_lower for w in ['prefer', 'preference', 'workflow']):
            score += 1.5
        
        # Low utility patterns
        if any(w in content_lower for w in ['temporary', 'transient', 'one-time']):
            score -= 2.0
        if any(w in content_lower for w in ['raw output', 'tool result']):
            score -= 1.5
        
        # Category boost
        score *= self.CATEGORY_BOOSTS.get(category, 1.0)
        
        return max(0.0, min(10.0, score))
    
    def _calc_novelty(self, content: str, existing: List[Dict]) -> float:
        """Calculate novelty score (0-10)."""
        if not existing:
            return 8.0
        
        content_words = set(content.lower().split())
        max_similarity = 0.0
        
        for existing_memory in existing:
            existing_words = set(existing_memory.get('content', '').lower().split())
            if existing_words:
                intersection = len(content_words & existing_words)
                union = len(content_words | existing_words)
                if union > 0:
                    similarity = intersection / union
                    max_similarity = max(max_similarity, similarity)
        
        return max(0.0, min(10.0, 10.0 * (1.0 - max_similarity)))
    
    def _calc_specificity(self, content: str) -> float:
        """Calculate specificity score (0-10)."""
        score = 5.0
        
        # Coding markers
        if re.search(r'[A-Za-z]:\\|/home/|\.py|\.js|\.ts', content):
            score += 2.0
        if re.search(r'error|exception|401|403|404|500', content, re.IGNORECASE):
            score += 2.0
        if re.search(r'def\s+\w+|class\s+\w+|\w+\(\)', content):
            score += 1.0
        if re.search(r'v?\d+\.\d+\.?\d*', content):
            score += 1.0
        
        # Vague patterns (penalty)
        if re.search(r'something|somehow|maybe|perhaps', content, re.IGNORECASE):
            score -= 1.0
        
        return max(0.0, min(10.0, score))
    
    def _calc_position(self, index: int, total: int) -> float:
        """Calculate position score (0-10)."""
        if total <= 1:
            return 7.0
        
        relative = index / total
        
        if relative <= 0.10 or relative >= 0.90:
            return 9.0
        elif relative <= 0.25 or relative >= 0.75:
            return 7.0
        else:
            return 4.0


# ============================================================================
# PROMPT COMPRESSION
# ============================================================================

class PromptCompressor:
    """Compresses prompt files."""
    
    SYMBOL_REPLACEMENTS = {
        r'\bCorrect\b': '✅',
        r'\bWrong\b': '❌',
        r'\bWarning\b': '⚠️',
        r'\bCritical\b': '**CRITICAL**',
        r'\bAlways\b': '✅',
        r'\bNever\b': '❌',
        r'\bRequired\b': '⚠️',
        r'\bDisabled\b': '❌',
        r'\bEnabled\b': '✅',
        r'\bIMPORTANT\b': '⚠️',
        r'\bMandatory\b': '⚠️',
        r'\bRecommended\b': '✅',
    }
    
    FILLER_PHRASES = [
        r'Please note that',
        r'It is important to',
        r'Keep in mind that',
        r'Note that',
        r'In order to',
        r'This means that',
        r'For example',
        r'etc\.',
        r'and so on',
    ]
    
    HEADER_SHORTENING = {
        '## 🚀 Quick Start': '## 🚀 Start',
        '## 📁 Structure (Key Paths)': '## 📁 Structure',
        '## ⚙️ Config Files': '## ⚙️ Config',
        '## 🔌 MCP Servers': '## 🔌 MCP',
        '## 🎯 Token Optimization': '## 🎯 Tokens',
        '## ✅ Approval Modes': '## ✅ Modes',
        '## 🛠️ CLI Commands': '## 🛠️ Commands',
        '## 🧪 Testing': '## 🧪 Tests',
        '## 🎨 TUI Features': '## 🎨 TUI',
        '## 🐛 Common Mistakes': '## 🐛 Mistakes',
        '## 📞 Quick Reference': '## 📞 Ref',
        '## 📝 Pre-Commit Checklist': '## 📝 Checklist',
        '## 🔧 Environment Variables': '## 🔧 Env Vars',
        '## 🔧 MCP Troubleshooting': '## 🔧 Troubleshoot',
        '## Qwen Added Memories': '## 💾 Memories',
    }
    
    def compress(self, content: str, level: str = 'standard') -> str:
        """Compress markdown content."""
        result = content
        
        # Symbol replacements
        for pattern, replacement in self.SYMBOL_REPLACEMENTS.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Remove fillers
        for filler in self.FILLER_PHRASES:
            result = re.sub(filler, '', result, flags=re.IGNORECASE)
        
        # Shorten headers (standard and aggressive only)
        if level in ['standard', 'aggressive']:
            for original, shortened in self.HEADER_SHORTENING.items():
                result = result.replace(original, shortened)
        
        # Aggressive compression
        if level == 'aggressive':
            # Remove excessive blank lines
            result = re.sub(r'\n{3,}', '\n\n', result)
            # Remove spaces in table cells
            lines = result.split('\n')
            optimized = []
            for line in lines:
                if '|' in line:
                    cells = [cell.strip() for cell in line.split('|')]
                    line = '|'.join(cells)
                optimized.append(line)
            result = '\n'.join(optimized)
        
        return result


# ============================================================================
# MEMORY EXTRACTION
# ============================================================================

def extract_memories(content: str, file_type: str = 'auto') -> List[Dict]:
    """Extract memories from markdown content."""
    memories = []
    lines = content.split('\n')
    
    # Detection patterns
    memory_section_start = re.compile(r'^##+\s*(?:Qwen\s+)?Added\s+Memories', re.IGNORECASE)
    bullet_pattern = re.compile(r'^[-*]\s+(.+)$')
    
    in_memory_section = False
    category = 'project_context' if file_type == 'project' else 'general'
    
    # Auto-detect file type
    if file_type == 'auto':
        if 'rapidwebs-agent' in content.lower():
            file_type = 'project'
            category = 'project_context'
        elif 'HARDWARE & SYSTEM PROFILE' in content:
            file_type = 'global'
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check for memory section header
        if memory_section_start.search(line_stripped):
            in_memory_section = True
            continue
        
        # Check for end of section
        if in_memory_section and line_stripped.startswith('##') and not bullet_pattern.match(line_stripped):
            in_memory_section = False
            continue
        
        # Extract bullet points
        if in_memory_section:
            bullet_match = bullet_pattern.match(line_stripped)
            if bullet_match:
                memory_text = bullet_match.group(1).strip()
                if memory_text and len(memory_text) > 10:
                    # Categorize
                    mem_category = _categorize_memory(memory_text, file_type)
                    
                    memories.append({
                        'content': memory_text,
                        'category': mem_category,
                        'source': 'bullet_point',
                    })
    
    return memories


def _categorize_memory(content: str, file_type: str) -> str:
    """Categorize memory based on content."""
    content_lower = content.lower()
    
    if any(w in content_lower for w in ['architecture', 'NOT MCP', 'uses SkillManager']):
        return 'architecture_decision'
    if any(w in content_lower for w in ['must', 'critical', 'avoid', 'mistake', 'error', 'prevent', 'requirements']):
        return 'error_prevention'
    if any(w in content_lower for w in ['prefer', 'preference']):
        return 'user_preference'
    if any(w in content_lower for w in ['levels', 'tracking', 'duration', 'chain']):
        return 'implementation_detail'
    if any(w in content_lower for w in ['tool', 'tools', 'configured', 'MCP', 'API']):
        return 'tool_configuration'
    if any(w in content_lower for w in ['config', 'budget', 'token', 'log location', 'entry point']):
        return 'project_context'
    if any(w in content_lower for w in ['TUI', 'display', 'render', 'component']):
        return 'implementation_detail'
    
    return 'project_context' if file_type == 'project' else 'general'


# ============================================================================
# MAIN OPTIMIZER
# ============================================================================

@dataclass
class OptimizationResult:
    """Result of optimization operation."""
    file: str
    mode: str
    memory_stats: Dict = None
    compression_stats: Dict = None
    backup_file: Optional[str] = None
    output_file: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class PromptOptimizer:
    """Unified prompt optimizer."""
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        self.memory_scorer = MemoryScorer()
        self.compressor = PromptCompressor()
    
    def optimize_file(self, file_path: str) -> OptimizationResult:
        """Optimize a single file."""
        result = OptimizationResult(file=file_path, mode=self.config.mode)
        
        try:
            # Read file
            path = Path(file_path)
            if not path.exists():
                result.success = False
                result.error = f"File not found: {file_path}"
                return result
            
            content = path.read_text(encoding='utf-8')
            
            # Determine file type
            file_type = 'project' if 'rapidwebs-agent' in content.lower() else 'global'
            
            # Extract and score memories
            memories = extract_memories(content, file_type)
            scored_memories = self.memory_scorer.score_memories(memories)
            
            # Memory stats
            keep_count = sum(1 for m in scored_memories if m['decision'] == 'AUTO-ADMIT')
            review_count = sum(1 for m in scored_memories if m['decision'] == 'REVIEW')
            remove_count = sum(1 for m in scored_memories if m['decision'] == 'SUMMARIZE')
            
            result.memory_stats = {
                'total': len(memories),
                'keep': keep_count,
                'review': review_count,
                'remove': remove_count,
                'average_score': round(sum(m['composite'] for m in scored_memories) / len(scored_memories), 2) if scored_memories else 0,
            }
            
            # Compress content
            original_chars = len(content)
            compressed = self.compressor.compress(content, self.config.compression_level)
            compressed_chars = len(compressed)
            
            result.compression_stats = {
                'original_chars': original_chars,
                'compressed_chars': compressed_chars,
                'reduction_percent': round((1 - compressed_chars / original_chars) * 100, 1) if original_chars > 0 else 0,
            }
            
            # Apply mode-specific action
            if self.config.mode == 'report':
                # Just report, no changes
                pass
            
            elif self.config.mode == 'optimize':
                # Create backup
                if self.config.create_backups:
                    backup_path = path.parent / f"{path.name}.bak"
                    backup_path.write_text(content, encoding='utf-8')
                    result.backup_file = str(backup_path)
                
                # Write optimized content
                path.write_text(compressed, encoding='utf-8')
                result.output_file = str(path)
            
            elif self.config.mode == 'save':
                # Save to dedicated folder
                output_dir = Path(self.config.optimized_folder)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / path.name
                output_path.write_text(compressed, encoding='utf-8')
                result.output_file = str(output_path)
            
            return result
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            return result
    
    def generate_report(self, results: List[OptimizationResult]) -> str:
        """Generate optimization report."""
        lines = []
        lines.append("=" * 70)
        lines.append("PROMPT OPTIMIZATION REPORT")
        lines.append("=" * 70)
        lines.append(f"Mode: {self.config.mode.upper()}")
        lines.append(f"Files processed: {len(results)}")
        lines.append("")

        for result in results:
            lines.append("-" * 70)
            lines.append(f"File: {result.file}")
            status_icon = "[OK]" if result.success else "[FAIL]"
            lines.append(f"Status: {status_icon}")

            if result.error:
                lines.append(f"Error: {result.error}")
                continue

            if result.memory_stats:
                lines.append(f"Memories: {result.memory_stats['total']} total")
                lines.append(f"  Keep (>=7.0): {result.memory_stats['keep']}")
                lines.append(f"  Review (5.5-6.9): {result.memory_stats['review']}")
                lines.append(f"  Remove (<5.5): {result.memory_stats['remove']}")
                lines.append(f"  Average Score: {result.memory_stats['average_score']}")
            
            if result.compression_stats:
                lines.append(f"Compression: -{result.compression_stats['reduction_percent']}%")
                lines.append(f"  Original: {result.compression_stats['original_chars']:,} chars")
                lines.append(f"  Compressed: {result.compression_stats['compressed_chars']:,} chars")
            
            if result.backup_file:
                lines.append(f"Backup: {result.backup_file}")
            
            if result.output_file:
                lines.append(f"Output: {result.output_file}")
            
            lines.append("")
        
        lines.append("=" * 70)
        
        return '\n'.join(lines)


# ============================================================================
# CLI
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Unified Prompt Optimizer (Memory + Compression)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes (set via --mode or QWEN_OPT_MODE env var):
  report   - Generate optimization report only (no changes)
  optimize - Apply optimizations and update original files
  save     - Save optimized versions to dedicated folder

Examples:
  %(prog)s --input QWEN.md --mode report
  %(prog)s --input QWEN.md --mode optimize --backup
  %(prog)s --input QWEN.md --mode save --output-folder optimized-prompts
  %(prog)s --global --mode optimize
        """
    )
    
    parser.add_argument('--input', '-i', help='Input file')
    parser.add_argument('--output', '-o', help='Output file (for save mode)')
    parser.add_argument('--mode', '-m', choices=['report', 'optimize', 'save'],
                        help='Optimization mode')
    parser.add_argument('--global', '-g', dest='is_global', action='store_true',
                        help='Optimize global QWEN.md')
    parser.add_argument('--project', '-p', dest='is_project', action='store_true',
                        help='Optimize project QWEN.md')
    parser.add_argument('--min-score', type=float, default=5.5,
                        help='Minimum memory score to keep (default: 5.5)')
    parser.add_argument('--compression', choices=['light', 'standard', 'aggressive'],
                        default='standard', help='Compression level')
    parser.add_argument('--no-backup', action='store_true',
                        help='Disable backup creation')
    parser.add_argument('--output-folder', default='optimized-prompts',
                        help='Output folder for save mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--config', action='store_true',
                        help='Save current settings as default config')
    
    args = parser.parse_args()
    
    # Load config
    config = OptimizerConfig.load()
    
    # Override with command line args
    if args.mode:
        config.mode = args.mode
    if args.min_score:
        config.min_memory_score = args.min_score
    if args.compression:
        config.compression_level = args.compression
    if args.no_backup:
        config.create_backups = False
    if args.output_folder:
        config.optimized_folder = args.output_folder
    if args.verbose:
        config.verbose = True
    
    # Save config if requested
    if args.config:
        config.save()
        print(f"Configuration saved to: .qwen/optimizer-config.json")
        return 0
    
    # Determine input file
    input_file = None
    
    if args.is_global:
        global_paths = [Path.home() / '.qwen' / 'QWEN.md']
        for p in global_paths:
            if p.exists():
                input_file = str(p)
                break
    elif args.is_project:
        project_paths = [Path('QWEN.md')]
        for p in project_paths:
            if p.exists():
                input_file = str(p)
                break
    elif args.input:
        input_file = args.input
    
    if not input_file:
        parser.print_help()
        return 0
    
    # Optimize
    optimizer = PromptOptimizer(config)
    result = optimizer.optimize_file(input_file)
    
    # Report
    report = optimizer.generate_report([result])
    
    # Handle Windows console encoding
    try:
        print(report)
    except UnicodeEncodeError:
        # Fallback for Windows console
        sys.stdout.reconfigure(encoding='utf-8')
        print(report)
    
    return 0 if result.success else 1


if __name__ == '__main__':
    exit(main())
