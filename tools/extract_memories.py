#!/usr/bin/env python3
"""
Memory Extractor for Qwen Code CLI
===================================
Extracts memories from QWEN.md files for scoring with memory_scorer.py

Supports extraction from:
- "## Qwen Added Memories" sections
- "**Memories:**" lines
- Custom memory sections

Usage:
    python extract_memories.py --input QWEN.md --output memories.json
    python extract_memories.py --global --output global_memories.json
    python extract_memories.py --project --output project_memories.json
    python extract_memories.py --stdin --output memories.json

Author: RapidWebs Agent
Version: 1.0.0
Date: 2026-03-08
"""

import json
import re
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional


def extract_from_markdown(content: str, file_type: str = "auto") -> List[Dict]:
    """
    Extract memories from markdown content.
    
    Args:
        content: Markdown content
        file_type: "global", "project", or "auto"
    
    Returns:
        List of memory dictionaries
    """
    memories = []
    lines = content.split('\n')
    
    # Detection patterns
    memory_section_start = re.compile(r'^##+\s*(?:Qwen\s+)?Added\s+Memories', re.IGNORECASE)
    memories_line_pattern = re.compile(r'^\*\*Memories:\*\*\s*(.+)$')
    bullet_pattern = re.compile(r'^[-*]\s+(.+)$')
    
    in_memory_section = False
    current_category = "general"
    
    # Auto-detect file type
    if file_type == "auto":
        if "rapidwebs-agent" in content.lower() and "approval modes" in content.lower():
            file_type = "project"
            current_category = "project_context"
        elif "HARDWARE & SYSTEM PROFILE" in content or "OPERATIONAL WORKFLOW" in content:
            file_type = "global"
            current_category = "general"
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check for memory section header
        if memory_section_start.search(line_stripped):
            in_memory_section = True
            continue
        
        # Check for end of section (new header)
        if in_memory_section and line_stripped.startswith('##') and not bullet_pattern.match(line_stripped):
            in_memory_section = False
            continue
        
        # Extract from "**Memories:**" line
        memories_match = memories_line_pattern.match(line_stripped)
        if memories_match:
            memories_text = memories_match.group(1)
            # Split by common delimiters
            items = re.split(r',\s*(?=(?:Node|OS|Auth|Model|Sandbox))', memories_text)
            for item in items:
                item = item.strip()
                if item and len(item) > 5:
                    # Determine category based on content
                    category = categorize_memory(item, file_type)
                    memories.append({
                        'content': item,
                        'category': category,
                        'source': 'memories_line'
                    })
            continue
        
        # Extract bullet points from memory section
        if in_memory_section:
            bullet_match = bullet_pattern.match(line_stripped)
            if bullet_match:
                memory_text = bullet_match.group(1).strip()
                
                # Skip empty or very short items
                if not memory_text or len(memory_text) < 10:
                    continue
                
                # Determine category
                category = categorize_memory(memory_text, file_type)
                
                memories.append({
                    'content': memory_text,
                    'category': category,
                    'source': 'bullet_point',
                    'line_number': i + 1
                })
    
    return memories


def categorize_memory(content: str, file_type: str = "general") -> str:
    """
    Automatically categorize memory based on content.
    
    Args:
        content: Memory content
        file_type: "global" or "project"
    
    Returns:
        Category string
    """
    content_lower = content.lower()
    
    # Architecture decisions
    if any(term in content_lower for term in ['architecture', 'uses SkillManager', 'NOT MCP', 'design pattern']):
        return 'architecture_decision'
    
    # Error prevention
    if any(term in content_lower for term in ['must', 'critical', 'avoid', 'mistake', 'error', 'prevent', 'requirements']):
        return 'error_prevention'
    
    # User preferences
    if any(term in content_lower for term in ['prefer', 'preference', 'workflow', 'style']):
        return 'user_preference'
    
    # Implementation details
    if any(term in content_lower for term in ['levels', 'capture', 'tracking', 'duration', 'three levels', 'chain']):
        return 'implementation_detail'
    
    # Tool configuration
    if any(term in content_lower for term in ['tool', 'tools', 'configured', 'MCP', 'API', 'key:', 'ctx7']):
        return 'tool_configuration'
    
    # Project context
    if any(term in content_lower for term in ['config', 'budget', 'token', 'log location', 'entry point', 'version', 'python']):
        return 'project_context'
    
    # TUI specific
    if any(term in content_lower for term in ['TUI', 'display', 'render', 'UI', 'component']):
        return 'implementation_detail'
    
    # Default based on file type
    if file_type == "project":
        return 'project_context'
    else:
        return 'general'


def extract_from_file(file_path: str, file_type: str = "auto") -> List[Dict]:
    """
    Extract memories from a file.
    
    Args:
        file_path: Path to markdown file
        file_type: "global", "project", or "auto"
    
    Returns:
        List of memory dictionaries
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    content = path.read_text(encoding='utf-8')
    return extract_from_markdown(content, file_type)


def extract_from_stdin() -> List[Dict]:
    """Extract memories from stdin input."""
    content = sys.stdin.read()
    return extract_from_markdown(content, file_type="auto")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract memories from QWEN.md files for scoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input QWEN.md --output memories.json
  %(prog)s --global --output global_memories.json
  %(prog)s --project --output project_memories.json
  %(prog)s --stdin < QWEN.md --output memories.json
  %(prog)s --input QWEN.md --output memories.json --category project_context
        """
    )
    
    parser.add_argument('--input', '-i',
                        help='Input QWEN.md file path')
    parser.add_argument('--output', '-o',
                        help='Output JSON file path')
    parser.add_argument('--global', '-g',
                        dest='is_global',
                        action='store_true',
                        help='Extract from global QWEN.md')
    parser.add_argument('--project', '-p',
                        dest='is_project',
                        action='store_true',
                        help='Extract from project QWEN.md')
    parser.add_argument('--stdin', '-s',
                        action='store_true',
                        help='Read from stdin')
    parser.add_argument('--category',
                        default=None,
                        help='Override category for all memories')
    parser.add_argument('--min-length',
                        type=int,
                        default=10,
                        help='Minimum memory length (default: 10)')
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    memories = []
    source_file = None
    
    # Determine input source
    if args.is_global:
        # Try common global QWEN.md locations
        global_paths = [
            Path.home() / '.qwen' / 'QWEN.md',
            Path.home() / '.qwen-code' / 'QWEN.md',
        ]
        for path in global_paths:
            if path.exists():
                source_file = str(path)
                memories = extract_from_file(source_file, file_type="global")
                break
        
        if not memories:
            print("Error: Could not find global QWEN.md file", file=sys.stderr)
            print("Tried:", global_paths, file=sys.stderr)
            return 1
    
    elif args.is_project:
        # Try common project QWEN.md locations
        project_paths = [
            Path('QWEN.md'),
            Path('docs' ) / 'QWEN.md',
        ]
        for path in project_paths:
            if path.exists():
                source_file = str(path)
                memories = extract_from_file(source_file, file_type="project")
                break
        
        if not memories:
            print("Error: Could not find project QWEN.md file", file=sys.stderr)
            return 1
    
    elif args.input:
        source_file = args.input
        file_type = "auto"
        if 'global' in args.input.lower():
            file_type = "global"
        elif 'project' in args.input.lower() or 'rapidwebs' in args.input.lower():
            file_type = "project"
        
        memories = extract_from_file(args.input, file_type=file_type)
    
    elif args.stdin:
        memories = extract_from_stdin()
        source_file = "stdin"
    
    else:
        parser.print_help()
        return 0
    
    # Filter by minimum length
    if args.min_length:
        memories = [m for m in memories if len(m.get('content', '')) >= args.min_length]
    
    # Override category if specified
    if args.category:
        for memory in memories:
            memory['category'] = args.category
    
    # Add metadata
    for memory in memories:
        memory['source_file'] = source_file
        memory['extracted_at'] = __import__('datetime').datetime.now().isoformat()
    
    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(memories, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        if args.verbose:
            print(f"Extracted {len(memories)} memories from: {source_file}")
            print(f"Saved to: {args.output}")
    else:
        # Print to stdout
        print(json.dumps(memories, indent=2, ensure_ascii=False))
        
        if args.verbose:
            print(f"\n# Extracted {len(memories)} memories from: {source_file}", file=sys.stderr)
    
    # Print summary
    if args.verbose and memories:
        categories = {}
        for m in memories:
            cat = m.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\nCategory breakdown:", file=sys.stderr)
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    exit(main())
