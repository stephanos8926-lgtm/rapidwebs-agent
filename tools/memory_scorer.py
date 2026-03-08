#!/usr/bin/env python3
"""
Memory Value Scoring Script for Qwen Code CLI
=============================================
Implements the A-MAC (Adaptive Memory Admission Control) algorithm for 
evaluating and optimizing system prompt memories.

Based on research from:
- A-MAC Paper (arxiv.org/html/2603.04549v1)
- Qwen2.5-1M Technical Report
- Anthropic Context Engineering Best Practices
- AWS Bedrock Memory Architecture

Usage:
    python memory_scorer.py --input memories.txt --output scored_memories.txt
    python memory_scorer.py --interactive
    python memory_scorer.py --batch --input memories.json

Author: RapidWebs Agent
Version: 1.0.0
Date: 2026-03-08
"""

import json
import re
import math
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib


@dataclass
class MemoryItem:
    """Represents a single memory item for scoring."""
    id: str
    content: str
    category: str = "general"
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    
    # Scores (0-10)
    utility_score: float = 0.0
    novelty_score: float = 0.0
    recency_score: float = 0.0
    specificity_score: float = 0.0
    position_score: float = 0.0
    
    # Composite score
    composite_score: float = 0.0
    
    # Decision
    decision: str = "PENDING"
    rationale: str = ""


class MemoryScorer:
    """
    A-MAC based memory scoring system.
    
    Composite Score Formula:
    SCORE = (Utility × 0.35) + (Novelty × 0.25) + (Recency × 0.15) + 
            (Specificity × 0.15) + (Position × 0.10)
    
    Decision Thresholds:
    - Score ≥ 7.0: AUTO-ADMIT (~25% of memories)
    - Score 5.5-6.9: REVIEW/CONDITIONAL (~58% of memories)
    - Score < 5.5: AUTO-REJECT or SUMMARIZE (~17% of memories)
    """
    
    # A-MAC weights (from research paper with 5-fold cross-validation)
    WEIGHTS = {
        'utility': 0.35,    # Highest weight - Type Prior dominates
        'novelty': 0.25,    # Second highest
        'recency': 0.15,    # Medium weight
        'specificity': 0.15,  # Medium weight
        'position': 0.10    # Lowest weight
    }
    
    # Decision thresholds (optimal F1=0.583 at threshold 5.5)
    THRESHOLDS = {
        'auto_admit': 7.0,
        'review': 5.5,
        'reject': 0.0
    }
    
    # Category priorities (Type Prior factor)
    CATEGORY_PRIORITIES = {
        'architecture_decision': 1.2,
        'error_prevention': 1.15,
        'user_preference': 1.1,
        'implementation_detail': 1.1,
        'project_context': 1.05,
        'tool_configuration': 1.0,
        'session_summary': 0.9,
        'debug_context': 0.85,
        'raw_tool_output': 0.7,
        'conversational filler': 0.6
    }
    
    # Coding-specific markers for specificity boost
    CODING_MARKERS = {
        'file_path': 2.0,
        'error_code': 2.0,
        'function_name': 1.0,
        'exact_command': 2.0,
        'version_number': 1.0,
        'api_endpoint': 1.5,
        'config_value': 1.5
    }

    def __init__(self):
        self.existing_memories: List[str] = []
        self.scorer_version = "1.0.0"
    
    def set_existing_memories(self, memories: List[str]):
        """Set existing memories for novelty comparison."""
        self.existing_memories = memories
    
    def calculate_utility_score(self, content: str, category: str) -> float:
        """
        Calculate utility score (0-10).
        
        Question: How useful is this for future coding tasks?
        
        Scoring criteria:
        - 9-10: Reusable across ALL sessions; defines core constraints
        - 7-8: Reusable across MULTIPLE sessions; project-specific knowledge
        - 5-6: Session-spanning utility; TODOs; progress markers
        - 3-4: Single-session utility; intermediate state
        - 1-2: One-time use; transient state; raw tool output
        """
        score = 5.0  # Base score
        content_lower = content.lower()
        
        # High utility indicators
        high_utility_patterns = [
            (r'must|critical|always|never|required|mandatory', 2.0),
            (r'architecture|design pattern|system design', 2.0),
            (r'prevent|avoid|error|mistake|bug', 1.5),
            (r'preference|prefer|workflow|style', 1.5),
            (r'configuration|config|setting', 1.0),
            (r'tool|command|api|function', 1.0),
        ]
        
        for pattern, boost in high_utility_patterns:
            if re.search(pattern, content_lower):
                score += boost
        
        # Low utility indicators
        low_utility_patterns = [
            (r'temporary|transient|session-only|one-time', -2.0),
            (r'raw output|tool result|executed', -1.5),
            (r'conversational|filler|greeting', -1.5),
            (r'explored|tried|attempted|failed', -1.0),
            (r'dead-end|misused|wrong', -1.0),
        ]
        
        for pattern, penalty in low_utility_patterns:
            if re.search(pattern, content_lower):
                score += penalty
        
        # Category-based adjustment
        category_boost = self.CATEGORY_PRIORITIES.get(category, 1.0)
        score *= category_boost
        
        return max(0.0, min(10.0, score))
    
    def calculate_novelty_score(self, content: str) -> float:
        """
        Calculate novelty score (0-10).
        
        Question: How unique is this compared to existing memory?
        
        Uses simple text similarity (cosine similarity approximation).
        If similarity > 0.85 but content differs, retain higher-scoring memory.
        """
        if not self.existing_memories:
            return 8.0  # No existing memories = high novelty
        
        # Simple similarity check using word overlap
        content_words = set(content.lower().split())
        max_similarity = 0.0
        
        for existing in self.existing_memories:
            existing_words = set(existing.lower().split())
            
            # Jaccard similarity
            intersection = len(content_words & existing_words)
            union = len(content_words | existing_words)
            
            if union > 0:
                similarity = intersection / union
                max_similarity = max(max_similarity, similarity)
        
        # Convert similarity to novelty score
        # similarity 0.0 = novelty 10.0
        # similarity 1.0 = novelty 0.0
        novelty = 10.0 * (1.0 - max_similarity)
        
        return max(0.0, min(10.0, novelty))
    
    def calculate_recency_score(self, 
                                created_at: Optional[datetime] = None,
                                last_accessed: Optional[datetime] = None) -> float:
        """
        Calculate recency score (0-10).
        
        Question: How recently was this accessed/created?
        
        Formula: Recency = exp(-0.01 × hours_elapsed)
        Half-life ≈ 69 hours
        """
        # Use last_accessed if available, otherwise created_at
        reference_time = last_accessed or created_at
        
        if not reference_time:
            return 5.0  # Unknown time = medium score
        
        hours_elapsed = (datetime.now() - reference_time).total_seconds() / 3600
        
        # Exponential decay with 69-hour half-life
        score = 10.0 * math.exp(-0.01 * hours_elapsed)
        
        return max(0.0, min(10.0, score))
    
    def calculate_specificity_score(self, content: str) -> float:
        """
        Calculate specificity score (0-10).
        
        Question: How precise and actionable is this information?
        
        Coding-specific markers:
        - Contains file paths: +2
        - Contains error codes/messages: +2
        - Contains function/class names: +1
        - Contains exact commands: +2
        - Contains version numbers: +1
        """
        score = 5.0  # Base score
        
        # File paths
        if re.search(r'[A-Za-z]:\\|/home/|\.py|\.js|\.ts|\.json|\.yaml|\.yml', content):
            score += self.CODING_MARKERS['file_path']
        
        # Error codes/messages
        if re.search(r'error|exception|failed|401|403|404|500|traceback', content, re.IGNORECASE):
            score += self.CODING_MARKERS['error_code']
        
        # Function/class names
        if re.search(r'def\s+\w+|class\s+\w+|\w+\(\)|\w+\.\w+', content):
            score += self.CODING_MARKERS['function_name']
        
        # Exact commands
        if re.search(r'^\s*[a-z]+\s+|pip\s|npm\s|git\s|python\s', content, re.IGNORECASE):
            score += self.CODING_MARKERS['exact_command']
        
        # Version numbers
        if re.search(r'v?\d+\.\d+\.?\d*|python\s*3\.\d+', content, re.IGNORECASE):
            score += self.CODING_MARKERS['version_number']
        
        # API endpoints
        if re.search(r'/api/|http[s]?://|endpoint', content, re.IGNORECASE):
            score += self.CODING_MARKERS['api_endpoint']
        
        # Config values
        if re.search(r'=\s*["\']?[\w\-\.]+["\']?|:\s*\d+|:\s*true|:\s*false', content):
            score += self.CODING_MARKERS['config_value']
        
        # Penalize vague content
        vague_patterns = [
            r'something|somehow|maybe|perhaps|probably',
            r'kind of|sort of|a bit|somewhat',
            r'etc\.|and so on|and the like',
        ]
        
        for pattern in vague_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score -= 1.0
        
        return max(0.0, min(10.0, score))
    
    def calculate_position_score(self, 
                                  position: int = 0,
                                  total_items: int = 1) -> float:
        """
        Calculate position score (0-10).
        
        Question: Where is this positioned in the context window?
        
        "Lost in the middle" phenomenon:
        - First 10% or last 10%: High score (primacy/recency effect)
        - Middle 50%: Low score without markers
        """
        if total_items <= 1:
            return 7.0  # Single item = good position
        
        relative_position = position / total_items
        
        if relative_position <= 0.10 or relative_position >= 0.90:
            return 9.0  # First/last 10%
        elif relative_position <= 0.25 or relative_position >= 0.75:
            return 7.0  # First/last 25%
        else:
            return 4.0  # Middle 50%
    
    def calculate_composite_score(self, item: MemoryItem) -> float:
        """
        Calculate composite score using A-MAC formula.
        
        SCORE = (Utility × 0.35) + (Novelty × 0.25) + (Recency × 0.15) + 
                (Specificity × 0.15) + (Position × 0.10)
        """
        score = (
            item.utility_score * self.WEIGHTS['utility'] +
            item.novelty_score * self.WEIGHTS['novelty'] +
            item.recency_score * self.WEIGHTS['recency'] +
            item.specificity_score * self.WEIGHTS['specificity'] +
            item.position_score * self.WEIGHTS['position']
        )
        
        return round(score, 2)
    
    def make_decision(self, score: float, content: str) -> Tuple[str, str]:
        """
        Make admit/reject decision based on score.
        
        Returns: (decision, rationale)
        """
        if score >= self.THRESHOLDS['auto_admit']:
            return (
                "AUTO-ADMIT",
                f"High-value memory (score {score:.2f} ≥ {self.THRESHOLDS['auto_admit']}). "
                f"Actionable across sessions, prevents repeated errors."
            )
        elif score >= self.THRESHOLDS['review']:
            return (
                "REVIEW",
                f"Medium-value memory (score {score:.2f}). "
                f"Consider keeping if context space allows, or summarize."
            )
        else:
            # Check for red flags
            red_flags = self._check_red_flags(content)
            
            if red_flags:
                return (
                    "AUTO-REJECT",
                    f"Low-value memory (score {score:.2f} < {self.THRESHOLDS['review']}). "
                    f"Red flags: {', '.join(red_flags)}"
                )
            else:
                return (
                    "SUMMARIZE",
                    f"Low-value memory (score {score:.2f}). "
                    f"Consider summarizing or removing after TTL expiration."
                )
    
    def _check_red_flags(self, content: str) -> List[str]:
        """Check for automatic rejection candidates."""
        red_flags = []
        content_lower = content.lower()
        
        # Security risk: API keys
        if re.search(r'api[_-]?key\s*[=:]\s*["\']?[a-zA-Z0-9\-_]{20,}', content_lower):
            red_flags.append("Contains API key (security risk)")
        
        # Redundant patterns
        if re.search(r'^(as mentioned|as stated|as noted|recall that)', content_lower):
            red_flags.append("Redundant reference")
        
        # Raw tool output
        if re.search(r'^\s*```[\w]*\n.*\n```\s*$', content, re.DOTALL):
            if len(content) > 500:
                red_flags.append("Large code block (consider summarizing)")
        
        # Resolved/superseded
        if re.search(r'(was|used to|formerly|previously).*?(now|currently)', content_lower):
            red_flags.append("Superseded information")
        
        return red_flags
    
    def score_memory(self, 
                     content: str,
                     category: str = "general",
                     created_at: Optional[datetime] = None,
                     last_accessed: Optional[datetime] = None,
                     position: int = 0,
                     total_items: int = 1) -> MemoryItem:
        """
        Score a single memory item.
        
        Returns: MemoryItem with all scores and decision
        """
        # Create memory item
        item = MemoryItem(
            id=hashlib.md5(content.encode()).hexdigest()[:8],
            content=content,
            category=category,
            created_at=created_at,
            last_accessed=last_accessed
        )
        
        # Calculate individual scores
        item.utility_score = round(self.calculate_utility_score(content, category), 2)
        item.novelty_score = round(self.calculate_novelty_score(content), 2)
        item.recency_score = round(self.calculate_recency_score(created_at, last_accessed), 2)
        item.specificity_score = round(self.calculate_specificity_score(content), 2)
        item.position_score = round(self.calculate_position_score(position, total_items), 2)
        
        # Calculate composite score
        item.composite_score = self.calculate_composite_score(item)
        
        # Make decision
        item.decision, item.rationale = self.make_decision(item.composite_score, content)
        
        return item
    
    def score_memories_batch(self, 
                              memories: List[Dict]) -> List[MemoryItem]:
        """
        Score multiple memories in batch.
        
        Input format:
        [
            {
                "content": "Memory text",
                "category": "architecture_decision",
                "created_at": "2026-03-08T10:00:00",  # Optional
                "last_accessed": "2026-03-08T15:00:00"  # Optional
            },
            ...
        ]
        """
        # Set existing memories for novelty comparison
        existing = [m.get('content', '') for m in memories[:-1]]  # All but last
        self.set_existing_memories(existing)
        
        # Score each memory
        results = []
        for i, memory in enumerate(memories):
            created_at = None
            last_accessed = None
            
            if memory.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(memory['created_at'])
                except ValueError:
                    pass
            
            if memory.get('last_accessed'):
                try:
                    last_accessed = datetime.fromisoformat(memory['last_accessed'])
                except ValueError:
                    pass
            
            item = self.score_memory(
                content=memory.get('content', ''),
                category=memory.get('category', 'general'),
                created_at=created_at,
                last_accessed=last_accessed,
                position=i,
                total_items=len(memories)
            )
            
            results.append(item)
        
        return results
    
    def generate_report(self, scored_memories: List[MemoryItem]) -> str:
        """Generate a summary report of scored memories."""
        total = len(scored_memories)
        
        # Count decisions
        admit_count = sum(1 for m in scored_memories if m.decision == "AUTO-ADMIT")
        review_count = sum(1 for m in scored_memories if m.decision == "REVIEW")
        reject_count = sum(1 for m in scored_memories if m.decision == "AUTO-REJECT")
        summarize_count = sum(1 for m in scored_memories if m.decision == "SUMMARIZE")
        
        # Calculate average scores
        avg_composite = sum(m.composite_score for m in scored_memories) / total if total > 0 else 0
        avg_utility = sum(m.utility_score for m in scored_memories) / total if total > 0 else 0
        
        # Generate report
        report = []
        report.append("=" * 60)
        report.append("MEMORY SCORING REPORT")
        report.append("=" * 60)
        report.append(f"Total memories scored: {total}")
        report.append(f"Average composite score: {avg_composite:.2f}")
        report.append(f"Average utility score: {avg_utility:.2f}")
        report.append("")
        report.append("DECISION BREAKDOWN:")
        report.append(f"  AUTO-ADMIT (>=7.0):   {admit_count} ({admit_count/total*100:.1f}%)")
        report.append(f"  REVIEW (5.5-6.9):     {review_count} ({review_count/total*100:.1f}%)")
        report.append(f"  AUTO-REJECT (<5.5):   {reject_count} ({reject_count/total*100:.1f}%)")
        report.append(f"  SUMMARIZE:            {summarize_count} ({summarize_count/total*100:.1f}%)")
        report.append("")
        report.append("TOP MEMORIES (by composite score):")
        
        # Sort by composite score descending
        sorted_memories = sorted(scored_memories, key=lambda m: m.composite_score, reverse=True)
        
        for i, memory in enumerate(sorted_memories[:5], 1):
            report.append(f"  {i}. [{memory.composite_score:.2f}] {memory.decision}")
            report.append(f"     Content: {memory.content[:80]}...")
            report.append(f"     Rationale: {memory.rationale}")
            report.append("")
        
        if reject_count > 0:
            report.append("MEMORIES TO REMOVE:")
            for memory in scored_memories:
                if memory.decision == "AUTO-REJECT":
                    report.append(f"  - [{memory.composite_score:.2f}] {memory.content[:60]}...")
                    report.append(f"    Reason: {memory.rationale}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


def parse_memories_from_file(input_path: str) -> List[Dict]:
    """Parse memories from various file formats."""
    path = Path(input_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    content = path.read_text(encoding='utf-8')
    
    # JSON format
    if path.suffix == '.json':
        return json.loads(content)
    
    # Text format (one memory per line or bullet point)
    memories = []
    
    # Handle markdown bullet points
    if '- ' in content or '* ' in content:
        lines = content.split('\n')
        current_memory = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                if current_memory:
                    memories.append({
                        'content': ' '.join(current_memory),
                        'category': 'general'
                    })
                current_memory = [line[2:]]
            elif current_memory and line:
                current_memory.append(line)
        
        if current_memory:
            memories.append({
                'content': ' '.join(current_memory),
                'category': 'general'
            })
    else:
        # One memory per line
        for line in content.split('\n'):
            line = line.strip()
            if line:
                memories.append({
                    'content': line,
                    'category': 'general'
                })
    
    return memories


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Memory Value Scorer for Qwen Code CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input memories.txt --output scored_memories.txt
  %(prog)s --interactive
  %(prog)s --batch --input memories.json --output report.txt
  %(prog)s --content "Python agent uses SkillManager, NOT MCP"
        """
    )
    
    parser.add_argument('--input', '-i', 
                        help='Input file path (txt, json, or md)')
    parser.add_argument('--output', '-o',
                        help='Output file path for results')
    parser.add_argument('--batch', '-b',
                        action='store_true',
                        help='Batch processing mode')
    parser.add_argument('--interactive', '-I',
                        action='store_true',
                        help='Interactive mode')
    parser.add_argument('--content', '-c',
                        help='Score a single memory content string')
    parser.add_argument('--category',
                        default='general',
                        choices=['architecture_decision', 'error_prevention', 
                                 'user_preference', 'implementation_detail',
                                 'project_context', 'tool_configuration',
                                 'session_summary', 'debug_context',
                                 'raw_tool_output', 'conversational filler',
                                 'general'],
                        help='Memory category for scoring')
    
    args = parser.parse_args()
    
    scorer = MemoryScorer()
    
    # Interactive mode
    if args.interactive:
        print("=" * 60)
        print("MEMORY SCORER - INTERACTIVE MODE")
        print("=" * 60)
        print("Enter memories to score (one per line, empty line to finish):")
        print()
        
        memories = []
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    break
                memories.append({'content': line, 'category': args.category})
            except EOFError:
                break
        
        if memories:
            results = scorer.score_memories_batch(memories)
            print()
            print(scorer.generate_report(results))
            
            if args.output:
                Path(args.output).write_text(
                    json.dumps([asdict(r) for r in results], indent=2),
                    encoding='utf-8'
                )
                print(f"\nResults saved to: {args.output}")
        return
    
    # Single content mode
    if args.content:
        item = scorer.score_memory(
            content=args.content,
            category=args.category
        )
        
        print("=" * 60)
        print("MEMORY SCORE RESULT")
        print("=" * 60)
        print(f"Content: {item.content}")
        print(f"Category: {item.category}")
        print()
        print("INDIVIDUAL SCORES:")
        print(f"  Utility:     {item.utility_score:.2f} (weight: 0.35)")
        print(f"  Novelty:     {item.novelty_score:.2f} (weight: 0.25)")
        print(f"  Recency:     {item.recency_score:.2f} (weight: 0.15)")
        print(f"  Specificity: {item.specificity_score:.2f} (weight: 0.15)")
        print(f"  Position:    {item.position_score:.2f} (weight: 0.10)")
        print()
        print(f"COMPOSITE SCORE: {item.composite_score:.2f}")
        print(f"DECISION: {item.decision}")
        print(f"RATIONALE: {item.rationale}")
        print("=" * 60)
        
        # Encode for Windows console compatibility
        try:
            print()
        except UnicodeEncodeError:
            # Fallback for Windows console
            import sys
            sys.stdout.reconfigure(encoding='utf-8')
        return
    
    # Batch mode
    if args.input:
        try:
            memories = parse_memories_from_file(args.input)
            results = scorer.score_memories_batch(memories)
            
            # Generate report
            report = scorer.generate_report(results)
            
            # Handle Windows console encoding
            try:
                print(report)
            except UnicodeEncodeError:
                # Write to stdout with UTF-8 encoding
                import sys
                sys.stdout.reconfigure(encoding='utf-8')
                print(report)
            
            # Save results
            if args.output:
                output_path = Path(args.output)
                
                if output_path.suffix == '.json':
                    output_path.write_text(
                        json.dumps([asdict(r) for r in results], indent=2),
                        encoding='utf-8'
                    )
                else:
                    output_path.write_text(report, encoding='utf-8')
                
                print(f"\nResults saved to: {args.output}")
            
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return 1
    
    # No arguments - show help
    if not any([args.input, args.interactive, args.content]):
        parser.print_help()
    
    return 0


if __name__ == '__main__':
    exit(main())
