# -*- coding: utf-8 -*-
"""
Prompt Compressor for Qwen Code CLI
Compresses QWEN.md files using research-backed techniques.
"""

import re
import argparse
from pathlib import Path


class PromptCompressor:
    """Compresses QWEN.md files."""
    
    SYMBOL_REPLACEMENTS = {
        r'\bCorrect\b': '[OK]',
        r'\bWrong\b': '[X]',
        r'\bWarning\b': '[!]',
        r'\bCritical\b': '[!!]',
        r'\bAlways\b': '[+]',
        r'\bNever\b': '[-]',
        r'\bRequired\b': '[!]',
        r'\bDisabled\b': '[OFF]',
        r'\bEnabled\b': '[ON]',
    }
    
    FILLER_PHRASES = [
        r'Please note that',
        r'It is important to',
        r'Keep in mind that',
        r'Note that',
        r'In order to',
        r'This means that',
        r'For example',
        r'etc.',
    ]
    
    def compress(self, content):
        """Compress markdown content."""
        result = content
        
        # Symbol replacements
        for pattern, replacement in self.SYMBOL_REPLACEMENTS.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Remove fillers
        for filler in self.FILLER_PHRASES:
            result = re.sub(filler, '', result, flags=re.IGNORECASE)
        
        # Remove excessive blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result


def main():
    parser = argparse.ArgumentParser(description='Compress QWEN.md files')
    parser.add_argument('--input', '-i', help='Input file')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--preview', action='store_true', help='Preview only')
    args = parser.parse_args()
    
    if not args.input:
        parser.print_help()
        return 0
    
    path = Path(args.input)
    if not path.exists():
        print(f"Error: File not found: {args.input}")
        return 1
    
    content = path.read_text(encoding='utf-8')
    original_lines = len(content.split('\n'))
    original_chars = len(content)
    
    compressor = PromptCompressor()
    compressed = compressor.compress(content)
    
    compressed_lines = len(compressed.split('\n'))
    compressed_chars = len(compressed)
    
    line_reduction = (1 - compressed_lines / original_lines) * 100 if original_lines > 0 else 0
    char_reduction = (1 - compressed_chars / original_chars) * 100 if original_chars > 0 else 0
    
    print("=" * 60)
    print("PROMPT COMPRESSION REPORT")
    print("=" * 60)
    print(f"Original:   {original_lines} lines, {original_chars:,} chars")
    print(f"Compressed: {compressed_lines} lines, {compressed_chars:,} chars")
    print(f"Line reduction: {line_reduction:.1f}%")
    print(f"Char reduction: {char_reduction:.1f}%")
    print("=" * 60)
    
    if args.output and not args.preview:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(compressed, encoding='utf-8')
        print(f"\nSaved to: {args.output}")
    elif args.preview:
        print("\n[PREVIEW MODE - No file saved]")
    
    return 0


if __name__ == '__main__':
    exit(main())
