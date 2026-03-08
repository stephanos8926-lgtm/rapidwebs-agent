#!/usr/bin/env python3
"""
Memory Optimizer Workflow Script
=================================
Complete workflow: Extract → Score → Report → Optimize

Combines extract_memories.py and memory_scorer.py into a single workflow.

Usage:
    python memory_optimizer.py --input QWEN.md --output optimized_QWEN.md
    python memory_optimizer.py --global --output optimized_global.md
    python memory_optimizer.py --project --output optimized_project.md
    python memory_optimizer.py --input QWEN.md --report-only

Author: RapidWebs Agent
Version: 1.0.0
Date: 2026-03-08
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Import our modules
from extract_memories import extract_from_file, categorize_memory
from memory_scorer import MemoryScorer, MemoryItem


def optimize_memories(memories: list, min_score: float = 5.5) -> dict:
    """
    Optimize memories based on scores.
    
    Args:
        memories: List of memory dictionaries
        min_score: Minimum score to keep (default: 5.5)
    
    Returns:
        Optimization report dictionary
    """
    scorer = MemoryScorer()
    
    # Score all memories
    scored = scorer.score_memories_batch(memories)
    
    # Categorize by decision
    keep = []
    review = []
    remove = []
    
    for item in scored:
        if item.decision == "AUTO-ADMIT":
            keep.append(item)
        elif item.decision == "REVIEW":
            review.append(item)
        else:  # AUTO-REJECT or SUMMARIZE
            remove.append(item)
    
    # Generate report
    report = {
        'total': len(scored),
        'keep_count': len(keep),
        'review_count': len(review),
        'remove_count': len(remove),
        'keep_percentage': len(keep) / len(scored) * 100 if scored else 0,
        'average_score': sum(m.composite_score for m in scored) / len(scored) if scored else 0,
        'keep_items': [m.content for m in keep],
        'review_items': [m.content for m in review],
        'remove_items': [{'content': m.content, 'reason': m.rationale, 'score': m.composite_score} for m in remove],
        'scored_items': [
            {
                'content': m.content,
                'category': m.category,
                'score': m.composite_score,
                'decision': m.decision,
                'rationale': m.rationale
            }
            for m in scored
        ]
    }
    
    return report


def generate_optimized_markdown(original_content: str, report: dict, file_type: str = "project") -> str:
    """
    Generate optimized markdown with filtered memories.
    
    Args:
        original_content: Original markdown content
        report: Optimization report
        file_type: "global" or "project"
    
    Returns:
        Optimized markdown content
    """
    lines = original_content.split('\n')
    output_lines = []
    
    in_memory_section = False
    memory_section_header = None
    memories_written = False
    
    import re
    memory_section_pattern = re.compile(r'^##+\s*(?:Qwen\s+)?Added\s+Memories', re.IGNORECASE)
    bullet_pattern = re.compile(r'^[-*]\s+')
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check for memory section start
        if memory_section_pattern.search(line_stripped):
            in_memory_section = True
            memory_section_header = line
            memories_written = False
            
            # Add header
            output_lines.append(line)
            output_lines.append('')
            
            # Add optimized memories
            for content in report['keep_items']:
                output_lines.append(f'- {content}')
            
            # Add review items with comment
            if report['review_items']:
                output_lines.append('')
                output_lines.append('<!-- REVIEW: Consider keeping these if context space allows -->')
                for content in report['review_items']:
                    output_lines.append(f'- {content}')
            
            memories_written = True
            continue
        
        # Skip bullet points if we're in memory section and already wrote optimized memories
        if in_memory_section and bullet_pattern.match(line_stripped):
            continue
        
        # Check for end of section
        if in_memory_section and line_stripped.startswith('##') and not bullet_pattern.match(line_stripped):
            in_memory_section = False
        
        # Add line if not skipped
        if not (in_memory_section and not memories_written):
            output_lines.append(line)
    
    # Handle "**Memories:**" line
    memories_line_pattern = re.compile(r'^\*\*Memories:\*\*\s*(.+)$')
    final_output = []
    
    for line in output_lines:
        memories_match = memories_line_pattern.match(line.strip())
        if memories_match:
            # Replace with high-score memories only
            if report['keep_items']:
                final_output.append('<!-- Optimized memories - see Qwen Added Memories section -->')
            else:
                final_output.append(line)
        else:
            final_output.append(line)
    
    return '\n'.join(final_output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Complete memory optimization workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input QWEN.md --output optimized_QWEN.md
  %(prog)s --global --output optimized_global.md
  %(prog)s --project --output optimized_project.md
  %(prog)s --input QWEN.md --report-only
  %(prog)s --input QWEN.md --min-score 6.0 --output optimized.md
        """
    )
    
    parser.add_argument('--input', '-i',
                        help='Input QWEN.md file')
    parser.add_argument('--output', '-o',
                        help='Output optimized QWEN.md file')
    parser.add_argument('--global', '-g',
                        dest='is_global',
                        action='store_true',
                        help='Optimize global QWEN.md')
    parser.add_argument('--project', '-p',
                        dest='is_project',
                        action='store_true',
                        help='Optimize project QWEN.md')
    parser.add_argument('--report-only',
                        action='store_true',
                        help='Generate report only, no file modification')
    parser.add_argument('--min-score',
                        type=float,
                        default=5.5,
                        help='Minimum score to keep memories (default: 5.5)')
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine input file
    input_file = None
    
    if args.is_global:
        global_paths = [
            Path.home() / '.qwen' / 'QWEN.md',
        ]
        for path in global_paths:
            if path.exists():
                input_file = str(path)
                break
    elif args.is_project:
        project_paths = [
            Path('QWEN.md'),
        ]
        for path in project_paths:
            if path.exists():
                input_file = str(path)
                break
    elif args.input:
        input_file = args.input
    
    if not input_file:
        parser.print_help()
        return 1
    
    # Extract memories
    if args.verbose:
        print(f"Extracting memories from: {input_file}")
    
    file_type = "global" if args.is_global else "project"
    memories = extract_from_file(input_file, file_type=file_type)
    
    if not memories:
        print(f"No memories found in: {input_file}")
        return 1
    
    if args.verbose:
        print(f"Found {len(memories)} memories")
    
    # Optimize memories
    report = optimize_memories(memories, min_score=args.min_score)
    
    # Print report
    print("=" * 60)
    print("MEMORY OPTIMIZATION REPORT")
    print("=" * 60)
    print(f"Source: {input_file}")
    print(f"Total memories: {report['total']}")
    print(f"Keep (score >= 7.0): {report['keep_count']} ({report['keep_percentage']:.1f}%)")
    print(f"Review (5.5-6.9): {report['review_count']}")
    print(f"Remove (score < 5.5): {report['remove_count']}")
    print(f"Average score: {report['average_score']:.2f}")
    print()
    
    if report['keep_items']:
        print("MEMORIES TO KEEP:")
        for i, content in enumerate(report['keep_items'][:5], 1):
            print(f"  {i}. {content[:70]}...")
        if len(report['keep_items']) > 5:
            print(f"  ... and {len(report['keep_items']) - 5} more")
        print()
    
    if report['remove_items']:
        print("MEMORIES TO REMOVE:")
        for item in report['remove_items']:
            print(f"  - [{item['score']:.2f}] {item['content'][:50]}...")
            print(f"    Reason: {item['reason']}")
        print()
    
    print("=" * 60)
    
    # Generate optimized file
    if args.output and not args.report_only:
        original_content = Path(input_file).read_text(encoding='utf-8')
        optimized_content = generate_optimized_markdown(original_content, report, file_type)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(optimized_content, encoding='utf-8')
        
        print(f"\nOptimized file saved to: {args.output}")
        print(f"Original: {len(memories)} memories → Optimized: {report['keep_count'] + report['review_count']} memories")
    
    # Save detailed report
    if args.verbose:
        report_path = Path(input_file).parent / 'memory_optimization_report.json'
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"Detailed report saved to: {report_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())
